from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore

from app.core.config import settings

@lru_cache(maxsize=1)
def get_vectorstore() -> QdrantVectorStore:
    embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model)
    return QdrantVectorStore.from_existing_collection(
        embedding=embeddings,
        collection_name=settings.qdrant_collection,
        path=settings.qdrant_path
    )