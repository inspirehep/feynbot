# Feynbot: talking with INSPIRE
This demo has been built following the official LlamaIndex [Starter Tutorial (Local Models)](https://docs.llamaindex.ai/en/stable/getting_started/starter_example_local/). It also implements index persistence from [Starter Tutorial (OpenAI)](https://docs.llamaindex.ai/en/stable/getting_started/starter_example/).

Model tested:

* Embedding model: [text-embedding-3-small](https://platform.openai.com/docs/models/embeddings)
* Generative model: [GPT-3.5-turbo](https://platform.openai.com/docs/models/gpt-3-5-turbo)

## Usage guide

1. Create a virtual environment and activate it:

`python3 -m venv .venv`

`source .venv/bin/activate`

2. Install the requirements:

`pip install -r requirements.txt`

3. Set up the OpenAI key in a environment variable:

`export OPENAI_API_KEY=<your_openai_api_key>`

3. Launch the app:

`python3 src/demo.py`
