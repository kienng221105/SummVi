from dataclasses import dataclass, field
from underthesea import ner, word_tokenize
@dataclass
class Entity:
    text: str
    label: str      
    doc_id: str
    sentence_idx: int
    normalized: str = ""
@dataclass
class Relation:
    source: str     
    target: str      
    relation_type: str 
    doc_id: str
    sentence_idx: int
    weight: float = 1.0

class NERExtractor:
    VALID_LABELS = {"PER", "ORG", "LOC", "MISC"}
    def extract(
        self,
        doc_id: str,
        sentences: list[str], 
    ) -> tuple[list[Entity], list[Relation]]:
        all_entities = []
        all_relations = []
        for idx, sentence in enumerate(sentences):
            entities = self._extract_entities(sentence, doc_id, idx)
            relations = self._extract_relations(entities, doc_id, idx)
            all_entities.extend(entities)
            all_relations.extend(relations)
        return all_entities, all_relations

    def _extract_entities(
        self,
        sentence: str,
        doc_id: str,
        sentence_idx: int,
    ) -> list[Entity]:
        try:
            tagged = ner(sentence)
        except Exception:
            return []
        entities = []
        current_entity_tokens = []
        current_label = ""
        for token, _, _, ne_tag in tagged:
            if ne_tag.startswith("B-"):
                if current_entity_tokens:
                    entities.append(self._build_entity(
                        current_entity_tokens,
                        current_label,
                        doc_id,
                        sentence_idx,
                    ))
                current_entity_tokens = [token]
                current_label = ne_tag[2:]
            elif ne_tag.startswith("I-") and current_label:
                current_entity_tokens.append(token)
            else:
                if current_entity_tokens:
                    entities.append(self._build_entity(
                        current_entity_tokens,
                        current_label,
                        doc_id,
                        sentence_idx,
                    ))
                current_entity_tokens = []
                current_label = ""
        if current_entity_tokens:
            entities.append(self._build_entity(
                current_entity_tokens,
                current_label,
                doc_id,
                sentence_idx,
            ))
        return [e for e in entities if e.label in self.VALID_LABELS]

    def _build_entity(
        self,
        tokens: list[str],
        label: str,
        doc_id: str,
        sentence_idx: int,
    ) -> Entity:
        text = " ".join(tokens)
        return Entity(
            text=text,
            label=label,
            doc_id=doc_id,
            sentence_idx=sentence_idx,
        )

    def _extract_relations(
        self,
        entities: list[Entity],
        doc_id: str,
        sentence_idx: int,
    ) -> list[Relation]:
        relations = []
        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                relations.append(Relation(
                    source=entities[i].text,
                    target=entities[j].text,
                    relation_type="co-occurrence",
                    doc_id=doc_id,
                    sentence_idx=sentence_idx,
                    weight=1.0,
                ))
        return relations
