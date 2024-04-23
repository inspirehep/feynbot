import logging
import sys
import os

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core import Settings
from llama_index.core import StorageContext
from llama_index.core import load_index_from_storage
from llama_index.llms.openai import OpenAI


def index_documents(persist_dir):
    if not os.path.exists(persist_dir):
        # load the documents and create the index
        documents = SimpleDirectoryReader("../toy_data").load_data()
        index = VectorStoreIndex.from_documents(documents)
        # store it for later
        index.storage_context.persist(persist_dir=persist_dir)
    else:
        # load the existing index
        storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
        index = load_index_from_storage(storage_context)
    return index

def get_response(query):
    # set global settings config
    llm = OpenAI(model="gpt-3.5-turbo", temperature=0)
    Settings.llm = llm
    Settings.chunk_size = 512

    # check if storage already exists
    PERSIST_DIR = "../storage"
    index = index_documents(PERSIST_DIR)

    query_engine = index.as_query_engine(
        similarity_top_k=3,
        streaming=True,
    )

    # query = (
    #     "How does the 1-loop R´enyi entropy in LCFT compare to that in ordinary CFT, "
    #     "particularly regarding the introduction of a new primary operator and the "
    #     "contributions of quasiprimary operators?"
    # )

    response = query_engine.query(query)
    # response.print_response_stream()

    return response
