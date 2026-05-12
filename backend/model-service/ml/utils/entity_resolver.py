from ml.utils.ner_extractor import Entity, Relation
from underthesea import word_tokenize
import numpy as np
class EntityResolver:
    def resolve(
        self,
        entities: list[Entity],
    ) -> tuple[list[Entity], dict[str, str]]:
        alias_map = {}
        canonical_map = {}
        for entity in entities:
            normalized = self._normalize(entity.text)
            entity.normalized = normalized
            if normalized in canonical_map:
                alias_map[entity.text] = canonical_map[normalized].text
                continue
            matched = self._find_substring_match(normalized, canonical_map)
            if matched:
                alias_map[entity.text] = canonical_map[matched].text
                continue
            canonical_map[normalized] = entity
        canonical_entities = list(canonical_map.values())
        return canonical_entities, alias_map

    def apply_aliases(
        self,
        relations: list[Relation],
        alias_map: dict[str, str],
    ) -> list[Relation]:
        resolved = []
        for rel in relations:
            resolved.append(Relation(
                source=alias_map.get(rel.source, rel.source),
                target=alias_map.get(rel.target, rel.target),
                relation_type=rel.relation_type,
                doc_id=rel.doc_id,
                sentence_idx=rel.sentence_idx,
                weight=rel.weight,
            ))
        return resolved

    def _normalize(self, text: str) -> str:
        honorifics = [
            "ông", "bà", "anh", "chị", "em", "cô", "chú",
            "giáo sư", "tiến sĩ", "gs", "ts", "ths", "bs",
        ]
        text = text.lower().strip()
        for h in honorifics:
            text = text.replace(h + " ", "")
        return " ".join(text.split())

    def _find_substring_match(
        self,
        normalized: str,
        canonical_map: dict,
    ) -> str | None:
        for key in canonical_map:
            if normalized in key or key in normalized:
                if normalized[0] == key[0]:
                    return key
        return None
