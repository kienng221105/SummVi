import json
import re
import numpy as np
import torch
from dataclasses import dataclass, field
from rouge_score import rouge_scorer        
from bert_score import score as bert_score 
@dataclass
class SummaryEvalResult:
    rouge1: float
    rouge2: float
    rougeL: float
    bert_precision: float
    bert_recall: float
    bert_f1: float
    hallucination_rate: float
    negation_recall: float = 0.0    
    warnings: list[str] = field(default_factory=list)

@dataclass
class RetrievalEvalResult:
    mrr: float           
    ndcg_at_k: float       
    precision_at_k: float  
    k: int

@dataclass
class RerankerEvalResult:
    precision_before: float 
    precision_after: float  
    improvement: float    

@dataclass
class SystemEvalResult:
    summary_eval: SummaryEvalResult
    retrieval_eval: RetrievalEvalResult
    reranker_eval: RerankerEvalResult
    overall_score: float   
    warnings: list[str] = field(default_factory=list)

class EvaluationPipeline:
    def __init__(self, lang: str = "vi"):
        self.lang = lang
        self.rouge = rouge_scorer.RougeScorer(
            ["rouge1", "rouge2", "rougeL"],
            use_stemmer=False, 
        )

    def evaluate_summaries(
        self,
        predictions: list[str], 
        references: list[str],  
        sources: list[str] | None = None, 
    ) -> SummaryEvalResult:
        warnings = []
        if len(predictions) != len(references):
            warnings.append(
                f"Length mismatch: {len(predictions)} predictions "
                f"vs {len(references)} references"
            )
        if sources is not None and len(predictions) != len(sources):
            warnings.append(
                f"Length mismatch between predictions ({len(predictions)}) "
                f"and sources ({len(sources)})"
            )
        r1, r2, rl = self._compute_rouge(predictions, references)
        bp, br, bf1 = self._compute_bertscore(predictions, references)
        hall_rate = 0.0
        if sources is not None:
            hall_rate = self._compute_hallucination_rate(predictions, sources)
        else:
            warnings.append("sources not provided, hallucination rate set to 0")
        neg_recall = 0.0
        if sources is not None:
            neg_recall = self._compute_negation_recall(predictions, sources)
        else:
            warnings.append("sources not provided, negation recall set to 0")
        return SummaryEvalResult(
            rouge1=r1,
            rouge2=r2,
            rougeL=rl,
            bert_precision=bp,
            bert_recall=br,
            bert_f1=bf1,
            hallucination_rate=hall_rate,
            negation_recall=neg_recall,
            warnings=warnings,
        )

    def _compute_rouge(
        self,
        predictions: list[str],
        references: list[str],
    ) -> tuple[float, float, float]:
        r1_scores, r2_scores, rl_scores = [], [], []
        for pred, ref in zip(predictions, references):
            if not pred.strip() or not ref.strip():
                continue
            scores = self.rouge.score(ref, pred)
            r1_scores.append(scores["rouge1"].fmeasure)
            r2_scores.append(scores["rouge2"].fmeasure)
            rl_scores.append(scores["rougeL"].fmeasure)
        return (
            float(np.mean(r1_scores)) if r1_scores else 0.0,
            float(np.mean(r2_scores)) if r2_scores else 0.0,
            float(np.mean(rl_scores)) if rl_scores else 0.0,
        )

    def _compute_bertscore(
        self,
        predictions: list[str],
        references: list[str],
    ) -> tuple[float, float, float]:
        if not predictions or not references:
            return 0.0, 0.0, 0.0
        P, R, F1 = bert_score(
            predictions,
            references,
            model_type="bert-base-multilingual-cased",
            verbose=False,
        )
        return (
            float(torch.as_tensor(P).mean()),
            float(torch.as_tensor(R).mean()),
            float(torch.as_tensor(F1).mean()),
        )

    def _compute_hallucination_rate(
        self,
        predictions: list[str],
        sources: list[str],
    ) -> float:
        total_sentences = 0
        hallucinated = 0
        for pred, src in zip(predictions, sources):
            src_words = set(src.lower().split())
            pred_sentences = pred.split(".")
            for sentence in pred_sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                total_sentences += 1
                sentence_words = set(sentence.lower().split())
                overlap = sentence_words & src_words
                overlap_ratio = len(overlap) / max(len(sentence_words), 1)
                if overlap_ratio < 0.1:
                    hallucinated += 1
        return hallucinated / max(total_sentences, 1)

    def _compute_negation_recall(
        self,
        predictions: list[str],
        sources: list[str],
    ) -> float:
        NEG_WORDS = ['không', 'tránh', 'đừng', 'ngừng', 'cấm', 'chớ']
        recalls = []
        for pred, src in zip(predictions, sources):
            src_sents = re.split(r'(?<=[.!?])\s+', src)
            neg_sents = [s for s in src_sents if any(w in s.lower() for w in NEG_WORDS)]
            if not neg_sents:
                continue
            found = sum(1 for ns in neg_sents if ns.lower() in pred.lower())
            recalls.append(found / len(neg_sents))
        return float(np.mean(recalls)) if recalls else 0.0

    def evaluate_retrieval(
        self,
        queries: list[str],
        retrieved_lists: list[list[str]],  
        relevant_chunks: list[list[str]], 
        k: int = 5,
    ) -> RetrievalEvalResult:
        mrr_scores  = []
        ndcg_scores = []
        p_at_k      = []

        for retrieved, relevant in zip(retrieved_lists, relevant_chunks):
            relevant_set = set(relevant)
            mrr = self._compute_mrr(retrieved, relevant_set)
            mrr_scores.append(mrr)

            ndcg = self._compute_ndcg(retrieved[:k], relevant_set, k)
            ndcg_scores.append(ndcg)

            hits = sum(1 for c in retrieved[:k] if c in relevant_set)
            p_at_k.append(hits / k)

        return RetrievalEvalResult(
            mrr=float(np.mean(mrr_scores)) if mrr_scores else 0.0,
            ndcg_at_k=float(np.mean(ndcg_scores)) if ndcg_scores else 0.0,
            precision_at_k=float(np.mean(p_at_k)) if p_at_k else 0.0,
            k=k,
        )

    def _compute_mrr(
        self,
        retrieved: list[str],
        relevant_set: set[str],
    ) -> float:
        for rank, chunk in enumerate(retrieved, start=1):
            if chunk in relevant_set:
                return 1.0 / rank
        return 0.0

    def _compute_ndcg(
        self,
        retrieved: list[str],
        relevant_set: set[str],
        k: int = 5,
    ) -> float:
        dcg = sum(
            1.0 / np.log2(rank + 1)
            for rank, chunk in enumerate(retrieved[:k], start=1)
            if chunk in relevant_set
        )
        ideal_hits = min(len(relevant_set), k)
        idcg = sum(
            1.0 / np.log2(rank + 1)
            for rank in range(1, ideal_hits + 1)
        )
        return dcg / idcg if idcg > 0 else 0.0

    def evaluate_reranker(
        self,
        pre_rerank_lists: list[list[str]], 
        post_rerank_lists: list[list[str]], 
        relevant_chunks: list[list[str]],
        k: int = 5,
    ) -> RerankerEvalResult:
        def precision(retrieved_lists):
            scores = []
            for retrieved, relevant in zip(retrieved_lists, relevant_chunks):
                relevant_set = set(relevant)
                hits = sum(1 for c in retrieved[:k] if c in relevant_set)
                scores.append(hits / k)
            return float(np.mean(scores)) if scores else 0.0

        p_before = precision(pre_rerank_lists)
        p_after  = precision(post_rerank_lists)

        return RerankerEvalResult(
            precision_before=p_before,
            precision_after=p_after,
            improvement=p_after - p_before,
        )

    def evaluate_system(
        self,
        predictions: list[str],
        references: list[str],
        retrieved_lists: list[list[str]],
        post_rerank_lists: list[list[str]],
        relevant_chunks: list[list[str]],
        queries: list[str],
        sources: list[str] | None = None,
    ) -> SystemEvalResult:
        warnings = []
        summary_eval = self.evaluate_summaries(predictions, references, sources)
        retrieval_eval = self.evaluate_retrieval(
            queries=queries,
            retrieved_lists=retrieved_lists,
            relevant_chunks=relevant_chunks,
        )
        reranker_eval = self.evaluate_reranker(
            pre_rerank_lists=retrieved_lists,
            post_rerank_lists=post_rerank_lists,
            relevant_chunks=relevant_chunks,
        )
        overall = self._compute_overall_score(
            summary_eval, retrieval_eval, reranker_eval
        )
        return SystemEvalResult(
            summary_eval=summary_eval,
            retrieval_eval=retrieval_eval,
            reranker_eval=reranker_eval,
            overall_score=overall,
            warnings=warnings,
        )

    def _compute_overall_score(
        self,
        summary: SummaryEvalResult,
        retrieval: RetrievalEvalResult,
        reranker: RerankerEvalResult,
    ) -> float:
        return (
            0.50 * summary.bert_f1 +
            0.25 * retrieval.ndcg_at_k +
            0.15 * summary.rougeL +
            0.10 * max(reranker.improvement + 0.5, 0)
        )

    def report(self, result: SystemEvalResult) -> str:
        s = result.summary_eval
        r = result.retrieval_eval
        rr = result.reranker_eval
        neg_str = f"{s.negation_recall:.4f}" if hasattr(s, 'negation_recall') else "N/A"
        return f"""
ROUGE-1:        {s.rouge1:.4f}          
ROUGE-2:        {s.rouge2:.4f}          
ROUGE-L:        {s.rougeL:.4f}          
BERTScore F1:   {s.bert_f1:.4f}          
Hallucination:  {s.hallucination_rate:.4f}          
Negation Recall:{neg_str}          
RETRIEVAL QUALITY (K={r.k})           
MRR:            {r.mrr:.4f}          
NDCG@{r.k}:       {r.ndcg_at_k:.4f}          
Precision@{r.k}:  {r.precision_at_k:.4f}          
RERANKER IMPACT                     
Before:         {rr.precision_before:.4f}          
After:          {rr.precision_after:.4f}          
Improvement:    {rr.improvement:+.4f}          
OVERALL SCORE:    {result.overall_score:.4f}          
        """.strip()

    def save(self, result: SystemEvalResult, path: str):
        import dataclasses
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dataclasses.asdict(result), f, ensure_ascii=False, indent=2)
