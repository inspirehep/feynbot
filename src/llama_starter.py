import os.path
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    Settings,
    load_index_from_storage,
)

from llama_index.core.embeddings import resolve_embed_model
from llama_index.llms.ollama import Ollama

# bge embedding model
Settings.embed_model = resolve_embed_model("local:BAAI/bge-small-en-v1.5")

# ollama
Settings.llm = Ollama(model="llama2", request_timeout=180.0)

# check if storage already exists
PERSIST_DIR = "./storage"
if not os.path.exists(PERSIST_DIR):
    # load the documents and create the index
    documents = SimpleDirectoryReader("toy_data").load_data()
    index = VectorStoreIndex.from_documents(documents)
    # store it for later
    index.storage_context.persist(persist_dir=PERSIST_DIR)
else:
    # load the existing index
    storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
    index = load_index_from_storage(storage_context)

# Either way we can now query the index
query_engine = index.as_query_engine()

query = (
    "How does the 1-loop R´enyi entropy in LCFT compare to that in ordinary CFT, ",
    "particularly regarding the introduction of a new primary operator and the ",
    "contributions of quasiprimary operators?"
)

print(query)

response = query_engine.query(query)

print(response)
