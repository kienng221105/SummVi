import torch
import torch.nn.functional as F
from typing import cast
from transformers import AutoTokenizer, AutoModel, PreTrainedModel, PreTrainedTokenizerBase
from dataclasses import dataclass, field
import numpy as np
@dataclass
class EmbeddedDocument:
    doc_id: str
    chunks: list[str]                 
    embeddings: np.ndarray              
    doc_embedding: np.ndarray           
    warnings: list[str] = field(default_factory=list)

class EmbeddingModel:
    MODEL_NAME = "vinai/phobert-base"
    tokenizer: PreTrainedTokenizerBase
    model: PreTrainedModel
    def __init__(
        self,
        model_name: str | None = None,
        cache_dir: str | None = None,
        device: str | None = None,
    ):
        self.device = device or (
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self.model_name = model_name or self.MODEL_NAME
        self.tokenizer = cast(PreTrainedTokenizerBase, AutoTokenizer.from_pretrained(self.model_name, cache_dir=cache_dir))
        self.model = AutoModel.from_pretrained(self.model_name, cache_dir=cache_dir)
        self.model.eval()
        self.model.to(self.device)

    def embed_document(
        self,
        doc_id: str,
        segmented_chunks: list[str],   
    ) -> EmbeddedDocument:
        warnings = []
        if not segmented_chunks:
            warnings.append(f"doc_id={doc_id}: no chunks to embed")
            empty = np.zeros(self.model.config.hidden_size)
            return EmbeddedDocument(
                doc_id=doc_id,
                chunks=segmented_chunks,
                embeddings=empty,
                doc_embedding=empty,
                warnings=warnings,
            )
        embeddings = self._encode_chunks(segmented_chunks)
        doc_embedding = embeddings.mean(axis=0)
        return EmbeddedDocument(
            doc_id=doc_id,
            chunks=segmented_chunks,
            embeddings=embeddings,
            doc_embedding=doc_embedding,
            warnings=warnings,
        )

    def embed_query(self, query: str) -> np.ndarray:
        from underthesea import word_tokenize
        segmented: str = str(word_tokenize(query, format="text"))  
        embeddings = self._encode_chunks([segmented])
        return embeddings[0]

    def _encode_chunks(
        self,
        chunks: list[str],
        batch_size: int = 16,
    ) -> np.ndarray:
        all_embeddings = []
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            batch_embeddings = self._encode_batch(batch)
            all_embeddings.append(batch_embeddings)
        return np.vstack(all_embeddings)

    def _encode_batch(self, batch: list[str]) -> np.ndarray:
        encoded = self.tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=256,    
            return_tensors="pt",
        ).to(self.device)
        with torch.no_grad():
            output = self.model(**encoded)
        embeddings = self._mean_pool(
            output.last_hidden_state,
            encoded["attention_mask"],
        )
        embeddings = F.normalize(embeddings, p=2, dim=1)
        return embeddings.cpu().numpy()

    def _mean_pool(
        self,
        token_embeddings: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> torch.Tensor:
        mask_expanded = (
            attention_mask
            .unsqueeze(-1)
            .expand(token_embeddings.size())
            .float()
        )
        sum_embeddings = torch.sum(token_embeddings * mask_expanded, dim=1)
        sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
        return sum_embeddings / sum_mask
