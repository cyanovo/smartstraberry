import os


def create_graph_vector_store():
    if os.environ.get("LOCAL_WINDOWS_MODE", "").lower() == "true":
        from .qdrant_graph_vector_store import QdrantGraphVectorStore

        return QdrantGraphVectorStore()
    from .milvus_graph_vector_store import MilvusGraphVectorStore

    return MilvusGraphVectorStore()
