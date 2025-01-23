# Feynbot: talking with INSPIRE

Feynbot is designed to help researchers explore high-energy physics content more intuitively by providing conversational access to the INSPIRE database for scientific literature.

## Usage guide

This guide assumes you have OpenSearch already available and running in your system.

### Local installation

1. Create a virtual environment and activate it:

`python3 -m venv .venv`

`source .venv/bin/activate`

2. Install the requirements:

`pip install -r requirements.txt`

3. Set up the OpenAI key in a environment variable:

`export OPENAI_API_KEY=<your_openai_api_key>`

3. Launch the app:

`python3 src/demo.py`

### Docker

1. Build the Docker image:

`docker build -t feynbot .`

2. Run the Docker container:

`docker run -e OPENAI_API_KEY=<your_openai_api_key> -p 7860:7860 feynbot`

This will start the Gradio web app, which will be accesible at http://localhost:7860.
