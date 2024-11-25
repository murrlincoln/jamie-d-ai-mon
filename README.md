# How to use this agent

0. Set up a virtual environment

```
python3 -m venv cdp-agentkit-env
source cdp-agentkit-env/bin/activate
```

1. Install the requirements

```
pip install -r requirements.txt
```

2. Set the CDP API keys

```
export CDP_API_KEY_NAME=<your-api-key-name>
export CDP_API_KEY_PRIVATE_KEY=<your-api-key-private-key>
```

3. Set the OpenAI API key

```
export OPENAI_API_KEY=<your-openai-api-key>
```

4. Run the agent

```
python jamie-d-ai-mon.py # if this doesn't work, try python3 jamie-d-ai-mon.py
```

# Notes
## Wallet
Right now, the wallet data is stored in a file called `wallet_data.txt`. This is not a great long-term solution. To create a new wallet on a new network, change the `wallet_data_file` variable in `jamie-d-ai-mon.py` to a new file name. If you want to create a new wallet on the same network, you can append a number to the end of the file name. 

## To-do
- Add in a Python-based Farcaster SDK for reading and posting
- Finalize how the wallet data is stored and loaded

