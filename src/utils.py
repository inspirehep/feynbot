import logging
import sys
import os
import yaml
import tiktoken

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core import Settings
from llama_index.core import StorageContext
from llama_index.core import load_index_from_storage
from llama_index.core.callbacks import CallbackManager, TokenCountingHandler
from llama_index.llms.openai import OpenAI


def load_config(config_path):
    with open(os.path.join(os.getcwd(), config_path)) as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    return config

def index_documents(config):
    persist_dir = config["llama_index"]["persist_dir"]
    if not os.path.exists(persist_dir):
        # load the documents and create the index
        documents = SimpleDirectoryReader(config["llama_index"]["data_dir"]).load_data()
        index = VectorStoreIndex.from_documents(documents)
        # store it for later
        index.storage_context.persist(persist_dir=persist_dir)
    else:
        # load the existing index
        storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
        index = load_index_from_storage(storage_context)
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
    index = index_documents(config)

    # Tokens used by indexing
    print("Indexing Embedding Tokens: ", token_counter.total_embedding_token_count)
    token_counter.reset_counts()

    query_engine = index.as_query_engine(
        similarity_top_k=config["llama_index"]["similarity_top_k"],
        streaming=config["llama_index"]["streaming"],
    )

    response = query_engine.query(query)

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

    return response
