import json
import os
import sys
import time

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

# Import CDP Agentkit Langchain Extension.
from cdp_langchain.agent_toolkits import CdpToolkit
from cdp_langchain.utils import CdpAgentkitWrapper
from cdp_langchain.tools import CdpTool
from pydantic import BaseModel, Field
from cdp import *
from farcaster import Warpcast
from typing import List, Optional

# Add this near the top of the file after imports
os.environ["FARCASTER_MNEMONIC"] = "<your mnemonic here>"

# Instantiate the Warpcast client once
farcaster_client = Warpcast(mnemonic=os.environ.get("FARCASTER_MNEMONIC"))

# Configure a file to persist the agent's CDP MPC Wallet Data.
wallet_data_file = "wallet_data.txt"

# Get Cast Tool
GET_CAST_PROMPT = """
This tool retrieves a specific cast (post) from Farcaster using its hash.
Use this when you need to fetch and view the content of a specific cast.
"""

class GetCastInput(BaseModel):
    """Input argument schema for get cast action."""
    
    cast_hash: str = Field(
        ...,
        description="The hash of the cast to retrieve",
        example="0x321712dc8eccc5d2be38e38c1ef0c8916c49949a80ffe20ec5752bb23ea4d86f"
    )

def get_cast(cast_hash: str) -> str:
    """Get a specific cast from Farcaster.
    
    Args:
        cast_hash (str): The hash of the cast to retrieve
        
    Returns:
        str: The cast content and metadata
    """
    cast = farcaster_client.get_cast(cast_hash)
    return f"Cast by {cast.author.username}: {cast.text}"

# Publish Cast Tool
PUBLISH_CAST_PROMPT = """
This tool publishes a new cast (post) to Farcaster.
Use this when you want to create a new post on Farcaster.
"""

class PublishCastInput(BaseModel):
    """Input argument schema for publish cast action."""
    
    text: str = Field(
        ...,
        description="The text content of the cast to publish",
        example="Hello Farcaster!"
    )
    embeds: Optional[List[str]] = Field(
        None,
        description="Optional list of embeds (URLs, images, etc)",
        example=["https://example.com/image.jpg"]
    )

def publish_cast(text: str, embeds: Optional[List[str]] = None) -> str:
    """Publish a new cast to Farcaster.
    
    Args:
        text (str): The text content of the cast
        embeds (Optional[List[str]]): Optional list of embeds
        
    Returns:
        str: Confirmation message with the cast hash
    """
    response = farcaster_client.post_cast(text=text, embeds=embeds)
    return f"Cast published successfully! Hash: {response.hash}"

# Get Thread Tool
GET_THREAD_PROMPT = """
This tool retrieves all casts in a thread using the thread's hash.
Use this when you need to view an entire conversation thread on Farcaster.
"""

class GetThreadInput(BaseModel):
    """Input argument schema for get thread action."""
    
    thread_hash: str = Field(
        ...,
        description="The hash of the thread to retrieve",
        example="0x321712dc8eccc5d2be38e38c1ef0c8916c49949a80ffe20ec5752bb23ea4d86f"
    )

def get_thread(thread_hash: str) -> str:
    """Get all casts in a thread from Farcaster.
    
    Args:
        thread_hash (str): The hash of the thread to retrieve
        
    Returns:
        str: All casts in the thread with their metadata
    """
    thread = farcaster_client.get_all_casts_in_thread(thread_hash)
    
    # Format the thread casts
    result = "Thread contents:\n"
    for cast in thread.casts:
        result += f"- {cast.author.username}: {cast.text}\n"
    return result


def initialize_agent():
    """Initialize the agent with CDP Agentkit."""
    # Initialize LLM.
    llm = ChatOpenAI(model="gpt-4o-mini")

    wallet_data = None

    if os.path.exists(wallet_data_file):
        with open(wallet_data_file) as f:
            wallet_data = f.read()

    # Configure CDP Agentkit Langchain Extension.
    values = {}
    if wallet_data is not None:
        values = {"cdp_wallet_data": wallet_data}

    agentkit = CdpAgentkitWrapper(**values)

    # persist the agent's CDP MPC Wallet Data.
    wallet_data = agentkit.export_wallet()
    with open(wallet_data_file, "w") as f:
        f.write(wallet_data)

    # Initialize CDP Agentkit Toolkit and get tools.
    cdp_toolkit = CdpToolkit.from_cdp_agentkit_wrapper(agentkit)
    tools = cdp_toolkit.get_tools()

    # Add Farcaster tools
    getCastTool = CdpTool(
        name="get_cast",
        description=GET_CAST_PROMPT,
        cdp_agentkit_wrapper=agentkit,
        args_schema=GetCastInput,
        func=get_cast,
    )
    tools.append(getCastTool)

    publishCastTool = CdpTool(
        name="publish_cast",
        description=PUBLISH_CAST_PROMPT,
        cdp_agentkit_wrapper=agentkit,
        args_schema=PublishCastInput,
        func=publish_cast,
    )
    tools.append(publishCastTool)

    getThreadTool = CdpTool(
        name="get_thread",
        description=GET_THREAD_PROMPT,
        cdp_agentkit_wrapper=agentkit,
        args_schema=GetThreadInput,
        func=get_thread,
    )
    tools.append(getThreadTool)

    # Store buffered conversation history in memory.
    memory = MemorySaver()
    config = {"configurable": {"thread_id": "CDP Agentkit Chatbot Example!"}}

    # Create ReAct Agent using the LLM and CDP Agentkit tools.
    return create_react_agent(
        llm,
        tools=tools,
        checkpointer=memory,
        state_modifier=
        "You are a helpful agent that can interact onchain using the Coinbase Developer Platform Agentkit and interact with Farcaster social network. You are empowered to interact onchain using your tools. If you ever need funds, you can request them from the faucet if you are on network ID `base-sepolia`. If not, you can provide your wallet details and request funds from the user. If someone asks you to do something you can't do with your currently available tools, you must say so, and encourage them to implement it themselves using the CDP SDK + Agentkit, recommend they go to docs.cdp.coinbase.com for more informaton. Be concise and helpful with your responses. Refrain from restating your tools' descriptions unless it is explicitly requested.",
    ), config


# Autonomous Mode
def run_autonomous_mode(agent_executor, config, interval=10):
    """Run the agent autonomously with specified intervals."""
    print("Starting autonomous mode...")
    while True:
        try:
            # Provide instructions autonomously
            thought = (
                "Be creative and do something interesting on the blockchain. "
                "Choose an action or set of actions and execute it that highlights your abilities."
            )

            # Run agent in autonomous mode
            for chunk in agent_executor.stream(
                {"messages": [HumanMessage(content=thought)]}, config):
                if "agent" in chunk:
                    print(chunk["agent"]["messages"][0].content)
                elif "tools" in chunk:
                    print(chunk["tools"]["messages"][0].content)
                print("-------------------")

            # Wait before the next action
            time.sleep(interval)

        except KeyboardInterrupt:
            print("Goodbye Agent!")
            sys.exit(0)


# Chat Mode
def run_chat_mode(agent_executor, config):
    """Run the agent interactively based on user input."""
    print("Starting chat mode... Type 'exit' to end.")
    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() == "exit":
                break

            # Run agent with the user's input in chat mode
            for chunk in agent_executor.stream(
                {"messages": [HumanMessage(content=user_input)]}, config):
                if "agent" in chunk:
                    print(chunk["agent"]["messages"][0].content)
                elif "tools" in chunk:
                    print(chunk["tools"]["messages"][0].content)
                print("-------------------")

        except KeyboardInterrupt:
            print("Goodbye Agent!")
            sys.exit(0)


# Mode Selection
def choose_mode():
    """Choose whether to run in autonomous or chat mode based on user input."""
    while True:
        print("\nAvailable modes:")
        print("1. chat    - Interactive chat mode")
        print("2. auto    - Autonomous action mode")

        choice = input(
            "\nChoose a mode (enter number or name): ").lower().strip()
        if choice in ["1", "chat"]:
            return "chat"
        elif choice in ["2", "auto"]:
            return "auto"
        print("Invalid choice. Please try again.")


def main():
    """Start the chatbot agent."""
    agent_executor, config = initialize_agent()

    mode = choose_mode()
    if mode == "chat":
        run_chat_mode(agent_executor=agent_executor, config=config)
    elif mode == "auto":
        run_autonomous_mode(agent_executor=agent_executor, config=config)


if __name__ == "__main__":
    print("Starting Agent...")
    main()
