from typing import List, Tuple, Optional

from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.embed import models
from qdrant_client.http.models import Distance, VectorParams, KeywordIndexType, KeywordIndexParams
from .embeddings import embeddings
from schema import DocumentModel
from langchain_core.documents import Document
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny

import os

# Use persistent client — replace host/port as needed
client = QdrantClient(url=os.getenv("Q_URL"), api_key=os.getenv("Q_API_KEY"), prefer_grpc=True)

collection_name = "my_collection"

# Only create collection if it doesn't exist
if collection_name not in [col.name for col in client.get_collections().collections]:
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )

vector_store = QdrantVectorStore(client=client, collection_name=collection_name, embedding=embeddings)


def insert_into_vectorstore(documents: list[DocumentModel], username: str):
    docs_to_add = []

    for document in documents:
        for page_num, page in enumerate(document.pages, start=1):
            for para_num, paragraph in enumerate(page.paragraphs, start=1):
                docs_to_add.append(
                    Document(
                        page_content=paragraph.refined_text,
                        metadata={
                            "group_id": username,  # Multitenancy partition key
                            "document_id": document.document_id,
                            "page": page_num,
                            "paragraph": para_num,
                            "filename": document.filename,
                            "chunk_id": f"{document.document_id}-{page_num}-{para_num}"  # <-- uniquely identifies a
                            # chunk
                        }
                    )
                )

    # Let Qdrant handle point UUIDs automatically
    print(docs_to_add)
    vector_store.add_documents(docs_to_add)


def delete_document_from_vectorstore(document_id: str, username: str):
    vector_store.delete(
        ids=Filter(
            must=[
                FieldCondition(key="metadata.group_id", match=MatchValue(value=username)),
                FieldCondition(key="metadata.document_id", match=MatchValue(value=document_id)),
            ]
        )
    )



def delete_user_vectors_from_vectorstore(username: str):
    vector_store.delete(
        filter=Filter(
            must=[
                FieldCondition(key="group_id", match=MatchValue(value=username))
            ]
        )
    )


def query_documents(
        query: str,
        username: str,
        document_ids: Optional[List[str]] = None,
        k: int = 5
) -> List[Tuple[str, float, str]]:
    """
    Perform a similarity search for a user across one or more documents.

    If `document_ids` is None or empty, the search includes all documents for that user.

    Returns a list of (chunk, score, document_id) tuples.
    """
    must_conditions = [FieldCondition(key="metadata.group_id", match=MatchValue(value=username))]

    if document_ids:
        must_conditions.append(
            FieldCondition(key="metadata.document_id", match=MatchAny(any=document_ids))
        )

    results = vector_store.similarity_search_with_score(
        query=query,
        k=k,
        filter=Filter(must=must_conditions)
    )

    print(results)
    return [
        {
            "document_id": doc.metadata.get("document_id"),
            "document_name": doc.metadata.get("filename"),  # filename is present
            "page": doc.metadata.get("page"),
            "paragraph": doc.metadata.get("paragraph"),
            "text": doc.page_content,
        }
        for doc, score in results
    ]
