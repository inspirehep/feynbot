import logging
import sys
import os
import re
import yaml

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))
from llama_index.llms.ollama import Ollama

from os import getenv
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    Settings,
)
from llama_index.core.query_engine import CitationQueryEngine
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.opensearch import (
    OpensearchVectorStore,
    OpensearchVectorClient,
)


def load_config(config_path):
    with open(os.path.join(os.getcwd(), config_path)) as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    return config


def create_opensearch_index(config):
    print("Creating and populating OpenSearch index collection")

    # load documents
    documents = SimpleDirectoryReader(config["llama_index"]["data_dir"]).load_data()

    # OpensearchVectorClient encapsulates logic for a single opensearch index with vector search enabled
    client = OpensearchVectorClient(
        str(getenv("OPENSEARCH_HOST")),
        str(getenv("OPENSEARCH_INDEX")),
        str(getenv("EMBEDDING_DIMENSIONS")),
        embedding_field=config["opensearch"]["embedding_field"],
        text_field=config["opensearch"]["text_field"],
        http_auth=(
            str(getenv("OPENSEARCH_USERNAME")),
            str(getenv("OPENSEARCH_PASSWORD")),
        ),
        verify_certs=False,
        use_ssl=True,
        url_prefix="/os",
    )

    # initialize vector store
    vector_store = OpensearchVectorStore(client)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # initialize an index using our sample data and the client we just created
    index = VectorStoreIndex.from_documents(
        documents=documents, storage_context=storage_context
    )
    return index


def get_opensearch_index(config):
    print("Loading existing OpenSearch index collection")

    # OpensearchVectorClient encapsulates logic for a single opensearch index with vector search enabled
    client = OpensearchVectorClient(
        str(getenv("OPENSEARCH_HOST")),
        str(getenv("OPENSEARCH_INDEX")),
        str(getenv("EMBEDDING_DIMENSIONS")),
        embedding_field=config["opensearch"]["embedding_field"],
        text_field=config["opensearch"]["text_field"],
        http_auth=(
            str(getenv("OPENSEARCH_USERNAME")),
            str(getenv("OPENSEARCH_PASSWORD")),
        ),
        verify_certs=False,
        use_ssl=True,
        url_prefix="/os",
    )

    # initialize vector store
    vector_store = OpensearchVectorStore(client)

    # initialize an index using our sample data and the client we just created
    index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
    return index


def postprocess_response(response):
    inspire_url = "https://inspirehep.net/literature?sort=mostrecent&size=25&page=1&q="

    references = {
        i: os.path.splitext(node.metadata["file_name"])[0]
        for i, node in enumerate(response.source_nodes)
    }

    # create a set to keep track of encountered files
    encountered_files = set()

    # create a new dictionary to store the updated data
    new_references = {}

    # initialize a variable to track the new index
    new_index = 1

    # create a dictionary to store the mapping of old indices to new indices
    index_mapping = {}

    for key, reference in references.items():
        # check if the file has been encountered before
        if reference not in encountered_files:
            # if not encountered, add it to the set and the new dictionary with updated index
            encountered_files.add(reference)
            new_references[new_index] = reference
            index_mapping[key] = new_index
            new_index += 1
        else:
            # if encountered, update the index mapping
            index_mapping[key] = min(
                index_mapping.get(k, float("inf"))
                for k, v in references.items()
                if v == reference
            )

    response = response.response if not isinstance(response, str) else response

    print("-" * 20)
    print("BEFORE posprocessing")
    print("Index mapping:", index_mapping)
    print("References:", references)
    print("New References:", new_references)
    print("Response:", response)
    print("-" * 20)

    # replace indices in the text according to the index_mapping
    for old_index, new_index in index_mapping.items():
        response = response.replace(f"[{old_index + 1}]", f"[{new_index}]")

    indices_in_text = set(map(int, re.findall(r"\[(\d+)\]", response)))
    # filter new_data to keep only items with indices appearing in the text
    new_references_filtered = {
        index: file_name
        for index, file_name in new_references.items()
        if index in indices_in_text
    }

    print("-" * 20)
    print("AFTER posprocessing")
    print("New References filtered:", new_references_filtered)
    print("Response:", response)
    print("-" * 20)

    # reference outputs as links in Markdown format
    md_references = "\n\n".join(
        [
            f"[[{i}] {reference}]({''.join([inspire_url, reference])})"
            for i, reference in new_references_filtered.items()
        ]
    )

    postprocess_response = [response, md_references]

    return postprocess_response


def get_response(manual_query, example_query):
    config = load_config("config.yaml")

    # use the manual query if set else use an example
    query = manual_query if manual_query else example_query

    # setup llamaindex settings
    Settings.embed_model = OllamaEmbedding(
        model_name=str(getenv("EMBEDDING_MODEL_NAME")),
        base_url=str(getenv("OPENAI_API_BASE")),
    )
    Settings.chunk_size = config["llama_index"]["chunk_size"]
    Settings.llm = Ollama(
        model=str(getenv("LLM_MODEL_NAME")),
        temperature=float(getenv("LLM_TEMPERATURE")),
        base_url=str(getenv("OPENAI_API_BASE")),
    )

    index = get_opensearch_index(config)

    query_engine = CitationQueryEngine.from_args(
        index,
        citation_chunk_size=1024,
        similarity_top_k=config["llama_index"]["similarity_top_k"],
    )

    response = query_engine.query(query)

    print("Number of source nodes:", len(response.source_nodes))
    for node in response.source_nodes:
        print(f"Node ID: {node.node_id}")
        print(f"Node Metadata: {node.metadata}")

    postprocessed_response = postprocess_response(response)

    return postprocessed_response
