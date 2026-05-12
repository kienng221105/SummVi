import networkx as nx
import community as community_louvain
from dataclasses import dataclass, field
from ml.utils.ner_extractor import Entity, Relation
@dataclass
class Community:
    community_id: int
    entities: list[str]         
    relations: list[Relation]  
    doc_ids: set[str]          
    summary: str = ""       

class KGBuilder:
    def build(
        self,
        entities: list[Entity],
        relations: list[Relation],
    ) -> nx.Graph:
        G = nx.Graph()
        for entity in entities:
            G.add_node(
                entity.text,
                label=entity.label,
                doc_ids=[entity.doc_id],
            )
        for rel in relations:
            if rel.source == rel.target:
                continue 
            if G.has_edge(rel.source, rel.target):
                G[rel.source][rel.target]["weight"] += rel.weight
            else:
                G.add_edge(
                    rel.source,
                    rel.target,
                    weight=rel.weight,
                    relation_type=rel.relation_type,
                    doc_ids=[rel.doc_id],
                )
        return G

    def detect_communities(
        self,
        G: nx.Graph,
        relations: list[Relation],
        entities: list[Entity],
    ) -> list[Community]:
        if len(G.nodes) == 0:
            return []
        partition = community_louvain.best_partition(G)
        community_nodes: dict[int, list[str]] = {}
        for node, comm_id in partition.items():
            community_nodes.setdefault(comm_id, []).append(node)
        communities = []
        entity_doc_map = {e.text: e.doc_id for e in entities}
        for comm_id, nodes in community_nodes.items():
            node_set = set(nodes)
            inner_relations = [
                r for r in relations
                if r.source in node_set and r.target in node_set
            ]
            doc_ids = {
                entity_doc_map[n]
                for n in nodes
                if n in entity_doc_map
            }
            communities.append(Community(
                community_id=comm_id,
                entities=nodes,
                relations=inner_relations,
                doc_ids=doc_ids,
            ))
        return communities

    def community_to_text(self, community: Community) -> str:
        entity_str = "Thực thể: " + ", ".join(community.entities[:20])
        relation_strs = []
        seen = set()
        for rel in community.relations[:30]: 
            key = f"{rel.source}|{rel.target}"
            if key not in seen:
                relation_strs.append(
                    f"{rel.source} - {rel.relation_type} - {rel.target}"
                )
                seen.add(key)
        relation_str = "Quan hệ: " + "; ".join(relation_strs)
        return f"{entity_str}\n{relation_str}"
