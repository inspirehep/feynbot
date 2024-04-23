# Feynbot: talking with INSPIRE
This demo has been built following the official LlamaIndex [Starter Tutorial (Local Models)](https://docs.llamaindex.ai/en/stable/getting_started/starter_example_local/). It also implements index persistence from [Starter Tutorial (OpenAI)](https://docs.llamaindex.ai/en/stable/getting_started/starter_example/).

Model tested:

* ~~Embedding model: [BAAI/bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5)~~
* ~~LLM: [Llama2](https://ollama.com/library/llama2) served through [Ollama](https://github.com/ollama/ollama)~~
* [GPT-3.5-turbo](https://platform.openai.com/docs/models/gpt-3-5-turbo)

## Usage guide

1. Create a virtual environment and activate it:

`python3 -m venv .venv`

2. Install the requirements:

`source .venv/bin/activate`

3. Set up the OpenAI key in a environment variable:

`export OPENAI_API_KEY=<your_openai_api_key>`

3. Launch the app:

`python3 src/demo.py`
