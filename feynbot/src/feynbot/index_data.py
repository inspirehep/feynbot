from llama_index.core import Settings
from llama_index.embeddings.ollama import OllamaEmbedding
from feynbot.app import load_config, create_opensearch_index
from os import getenv


if __name__ == "__main__":
    config = load_config("config.yaml")
    Settings.embed_model = OllamaEmbedding(
        model_name=str(getenv("EMBEDDING_MODEL_NAME")),
        base_url=str(getenv("OPENAI_API_BASE")),
    )

    Settings.chunk_size = config["llama_index"]["chunk_size"]

    try:
        index = create_opensearch_index(config)
    except:
        print("An error ocurred while creating the OpenSearch index")
