import chromadb
from chromadb.config import Settings
import numpy as np
from dataclasses import dataclass
@dataclass 
class VectorStore:
    persist_dir: str = "data/vector_store"
    collection_name: str = "documents"
    def __post_init__(self):
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},  
        )

    def add(
        self,
        doc_id: str,
        chunks: list[str],
        embeddings: np.ndarray,
        extra_metadata: dict | None = None,
    ):
        ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "doc_id": doc_id,
                "chunk_index": i,
                **(extra_metadata or {}),
            }
            for i in range(len(chunks))
        ]
        self.collection.add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings.tolist(),
            metadatas=metadatas,
        )

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        filter_doc_id: str | None = None,
    ) -> list[dict]:
        where = {"doc_id": filter_doc_id} if filter_doc_id else None
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        output = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            output.append({
                "doc_id": meta["doc_id"],
                "chunk": doc,
                "chunk_index": meta["chunk_index"],
                "score": 1 - dist, 
                "metadata": meta,
            })
        return output

    def search_by_type(
        self,
        query_embedding: np.ndarray,
        chunk_type: str,      
        top_k: int = 5,
    ) -> list[dict]:
        return self.search(
            query_embedding=query_embedding,
            top_k=top_k,
        )

    def get_all_doc_embeddings(self) -> dict[str, np.ndarray]:
        results = self.collection.get(include=["embeddings", "metadatas"])
        doc_chunks: dict[str, list] = {}
        for emb, meta in zip(results["embeddings"], results["metadatas"]):
            doc_id = meta["doc_id"]
            doc_chunks.setdefault(doc_id, []).append(emb)
        return {
            doc_id: np.mean(vecs, axis=0)
            for doc_id, vecs in doc_chunks.items()
        }

    def delete_document(self, doc_id: str):
        self.collection.delete(where={"doc_id": doc_id})
