import logging
import sys
import os
import yaml
import tiktoken
import chromadb

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

from llama_index.core import (
    VectorStoreIndex, 
    SimpleDirectoryReader, 
    StorageContext, 
    Settings
)
from llama_index.core.callbacks import CallbackManager, TokenCountingHandler
from llama_index.core.query_engine import CitationQueryEngine
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding

def load_config(config_path):
    with open(os.path.join(os.getcwd(), config_path)) as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    return config

def create_index(config):
    print("Creating index collection")

    # define embedding function
    embed_model = OpenAIEmbedding()

    # load documents
    documents = SimpleDirectoryReader(config["llama_index"]["data_dir"]).load_data()

    # create client and a new collection
    db = chromadb.PersistentClient(path=config["chroma_db"]["path"])
    chroma_collection = db.create_collection(config["chroma_db"]["collection"])

    # set up ChromaVectorStore and load in data
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_documents(
        documents, storage_context=storage_context, embed_model=embed_model
    )
    return index

def get_index(config):
    print("Getting index collection")

    # define embedding function
    embed_model = OpenAIEmbedding()

    # create client and a new collection
    db = chromadb.PersistentClient(path=config["chroma_db"]["path"])
    chroma_collection = db.get_collection(config["chroma_db"]["collection"])

    # set up ChromaVectorStore and load in data
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    index = VectorStoreIndex.from_vector_store(
        vector_store,
        embed_model=embed_model,
    )
    return index

def get_response(query):
    config = load_config("config.yaml")

    # set global settings config
    token_counter = TokenCountingHandler(tokenizer=tiktoken.encoding_for_model(config["llama_index"]["model"]).encode)
    llm = OpenAI(
        model=config["llama_index"]["model"],
        temperature=config["llama_index"]["temperature"]
    )
    Settings.llm = llm
    Settings.chunk_size = config["llama_index"]["chunk_size"]
    Settings.callback_manager = CallbackManager([token_counter])

    # check if storage already exists
    index = get_index(config)

    # Tokens used by indexing
    print("Indexing Embedding Tokens: ", token_counter.total_embedding_token_count)
    token_counter.reset_counts()

    query_engine = CitationQueryEngine.from_args(
        index,
        citation_chunk_size=1024,
        similarity_top_k=config["llama_index"]["similarity_top_k"]
    )

    response = query_engine.query(query)
    print("Number of source nodes:", len(response.source_nodes))
    for node in response.source_nodes:
        print(f"Node ID: {node.node_id}")
        print(f"Node Metadata: {node.metadata}")

    # Tokens used by querying
    print(
        "Query Embedding Tokens: ",
        token_counter.total_embedding_token_count,
        "\n",
        "LLM Prompt Tokens: ",
        token_counter.prompt_llm_token_count,
        "\n",
        "LLM Completion Tokens: ",
        token_counter.completion_llm_token_count,
        "\n",
        "Total LLM Token Count: ",
        token_counter.total_llm_token_count,
        "\n",
    )

    token_counter.reset_counts()

    return [response, "\n".join([f"[{i+1}] {node.metadata['file_name']}" for i, node in enumerate(response.source_nodes)])]
