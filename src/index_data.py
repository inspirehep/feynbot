from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from utils import load_config, create_opensearch_index

if __name__ == "__main__":
    config = load_config("config.yaml")
    Settings.embed_model = HuggingFaceEmbedding(model_name=config["llama_index"]["embedding_model"])
    Settings.chunk_size = config["llama_index"]["chunk_size"]
    
    try:
        index = create_opensearch_index(config)
    except:
        print("An error ocurred while creating the OpenSearch index")