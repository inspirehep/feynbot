import logging
import sys
import os
import re
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
from chromadb.config import Settings

def load_config(config_path):
    with open(os.path.join(os.getcwd(), config_path)) as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    return config

def _create_index(config):
    print("Creating index collection")

    # define embedding function
    embed_model = OpenAIEmbedding(
        # model=config["llama_index"]["embedding_model"],
        # embed_batch_size=10
        )

    # load documents
    documents = SimpleDirectoryReader(config["llama_index"]["data_dir"]).load_data()

    # create client and a new collection
    db = chromadb.PersistentClient(path=config["chroma_db"]["path"], settings=Settings(allow_reset=True))
    db.reset()
    chroma_collection = db.create_collection(config["chroma_db"]["collection"])

    # set up ChromaVectorStore and load in data
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_documents(
        documents, storage_context=storage_context, embed_model=embed_model
    )
    return index

def _get_index(config):
    print("Getting index collection")

    # define embedding function
    # embed_model = OpenAIEmbedding(model=config["llama_index"]["embedding_model"])
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


def postprocess_response(response):

    inspire_url = "https://inspirehep.net/literature?sort=mostrecent&size=25&page=1&q="

    references = {
        i: os.path.splitext(node.metadata['file_name'])[0]
        for i, node 
        in enumerate(response.source_nodes)
    }

    # # get only the first occurence of the reference to avoid duplicates
    # unique_references = {}
    # for k, v in references.items():
    #     unique_references.setdefault(v, k)
    # references = {v: k for k, v in unique_references.items()}

    # Create a set to keep track of encountered files
    encountered_files = set()

    # Create a new dictionary to store the updated data
    new_references = {}

    # Initialize a variable to track the new index
    new_index = 1

    # Create a dictionary to store the mapping of old indices to new indices
    index_mapping = {}

    for key, reference in references.items():
        # Check if the file has been encountered before
        if reference not in encountered_files:
            # If not encountered, add it to the set and the new dictionary with updated index
            encountered_files.add(reference)
            new_references[new_index] = reference
            index_mapping[key] = new_index
            new_index += 1
        else:
            # If encountered, update the index mapping
            index_mapping[key] = min(index_mapping.get(k, float('inf')) for k, v in references.items() if v == reference)

    response = response.response if not isinstance(response, str) else response
    
    print("-"*20)
    print("BEFORE posprocessing")
    print("Index mapping:", index_mapping)
    print("References:", references)
    print("New References:", new_references)
    print("Response:", response)
    print("-"*20)

    # Replace indices in the text according to the index_mapping
    for old_index, new_index in index_mapping.items():
        response = response.replace(f"[{old_index+1}]", f"[{new_index}]")

    indices_in_text = set(map(int, re.findall(r'\[(\d+)\]', response)))
    # Filter new_data to keep only items with indices appearing in the text
    new_references_filtered = {index: file_name for index, file_name in new_references.items() if index in indices_in_text}

    print("-"*20)
    print("AFTER posprocessing")
    print("New References filtered:", new_references_filtered)
    print("Response:", response)
    print("-"*20)
    

    # reference outputs as links in Markdown format
    md_references = "\n\n".join(
        [
            f"[[{i}] {reference}]({''.join([inspire_url, reference])})" 
            for i, reference 
            in new_references_filtered.items()
        ]
    )

    postprocess_response = [
        response, 
        md_references
    ]

    return postprocess_response


def get_response(manual_query, example_query):
    config = load_config("config.yaml")

    # Use the manual query if set else use an example
    query = manual_query if manual_query else example_query
    print(f"Query selected: {query}")

    # set global settings config
    token_counter = TokenCountingHandler(tokenizer=tiktoken.encoding_for_model(config["llama_index"]["llm_model"]).encode)
    llm = OpenAI(
        model=config["llama_index"]["llm_model"],
        temperature=config["llama_index"]["temperature"]
    )
    Settings.llm = llm
    Settings.chunk_size = config["llama_index"]["chunk_size"]
    # Settings.chunk_overlap = 20
    # maximum input size to the LLM
    # Settings.context_window = 4096
    # number of tokens reserved for text generation.
    # Settings.num_output = 256
    Settings.callback_manager = CallbackManager([token_counter])

    # check if storage already exists
    # index = _create_index(config)
    index = _get_index(config)

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

    postprocessed_response = postprocess_response(response)

    return postprocessed_response
