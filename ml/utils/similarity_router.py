import numpy as np
from typing import Any
from dataclasses import dataclass, field
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import AgglomerativeClustering
SIMILARITY_THRESHOLD = 0.65 
MIN_CLUSTER_SIZE     = 2  
class RouteType:
    KG           = "kg"    
    INDEPENDENT  = "independent" 
@dataclass
class DocumentGroup:
    group_id: str
    doc_ids: list[str]
    route: str                      
    avg_similarity: float            
    warnings: list[str] = field(default_factory=list)

@dataclass
class RouterOutput:
    groups: list[DocumentGroup]
    similarity_matrix: Any   
    doc_id_order: list[str]     

class SimilarityRouter:
    def __init__(
        self,
        threshold: float = SIMILARITY_THRESHOLD,
    ):
        self.threshold = threshold

    def route(
        self,
        doc_embeddings: dict[str, Any],
    ) -> RouterOutput:
        doc_ids = list(doc_embeddings.keys())
        vectors = np.vstack([doc_embeddings[d] for d in doc_ids])
        if len(doc_ids) == 1:
            return self._single_doc_output(doc_ids[0], vectors)
        sim_matrix = cosine_similarity(vectors)
        labels = self._cluster(sim_matrix, len(doc_ids))
        groups = self._build_groups(doc_ids, labels, sim_matrix)
        return RouterOutput(
            groups=groups,
            similarity_matrix=sim_matrix,
            doc_id_order=doc_ids,
        )

    def _cluster(
        self,
        sim_matrix: Any,
        n_docs: int,
    ) -> Any:
        if n_docs == 2:
            sim = sim_matrix[0, 1]
            if sim >= self.threshold:
                return np.array([0, 0])
            else:
                return np.array([0, 1])
        distance_matrix = 1 - sim_matrix
        np.fill_diagonal(distance_matrix, 0)
        clustering = AgglomerativeClustering(
            n_clusters=None,
            metric="precomputed",
            linkage="average",          
            distance_threshold=1 - self.threshold,
        )
        return clustering.fit_predict(distance_matrix)

    def _build_groups(
        self,
        doc_ids: list[str],
        labels: Any,
        sim_matrix: Any,
    ) -> list[DocumentGroup]:
        clusters: dict[int, list[int]] = {}
        for idx, label in enumerate(labels):
            clusters.setdefault(int(label), []).append(idx)
        groups = []
        for label, indices in clusters.items():
            doc_id_group = [doc_ids[i] for i in indices]
            avg_sim = self._avg_similarity(indices, sim_matrix)
            if len(indices) >= MIN_CLUSTER_SIZE:
                route = RouteType.KG
            else:
                route = RouteType.INDEPENDENT
            warnings = []
            if avg_sim < self.threshold and route == RouteType.KG:
                warnings.append(
                    f"Group {label}: avg similarity {avg_sim:.2f} is close "
                    f"to threshold — KG connections may be sparse"
                )
            groups.append(DocumentGroup(
                group_id=f"group_{label}",
                doc_ids=doc_id_group,
                route=route,
                avg_similarity=avg_sim,
                warnings=warnings,
            ))
        return groups

    def _avg_similarity(
        self,
        indices: list[int],
        sim_matrix: Any,
    ) -> float:
        if len(indices) == 1:
            return 1.0
        sims = []
        for i in range(len(indices)):
            for j in range(i + 1, len(indices)):
                sims.append(sim_matrix[indices[i], indices[j]])
        return float(np.mean(sims))

    def _single_doc_output(
        self,
        doc_id: str,
        vectors: Any,
    ) -> RouterOutput:
        return RouterOutput(
            groups=[DocumentGroup(
                group_id="group_0",
                doc_ids=[doc_id],
                route=RouteType.INDEPENDENT,
                avg_similarity=1.0,
            )],
            similarity_matrix=np.array([[1.0]]),
            doc_id_order=[doc_id],
        )
