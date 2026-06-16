from __future__ import annotations

import math
import re
from collections import Counter

from .clinical_rules import derive_clinical_labels
from .embedding_text import build_embedding_text
from .models import ClinicalRecord, KnowledgeDocument, RetrievalBundle, RetrievalResult


TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def cosine_similarity(left: Counter[str], right: Counter[str]) -> float:
    shared = set(left) & set(right)
    numerator = sum(left[token] * right[token] for token in shared)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


class HybridRetriever:
    def __init__(self, documents: list[KnowledgeDocument]) -> None:
        self.documents = documents
        self.document_vectors = {
            document.doc_id: Counter(tokenize(document.text)) for document in documents
        }

    def retrieve(self, record: ClinicalRecord, top_k: int = 3) -> RetrievalBundle:
        labels = derive_clinical_labels(record.vitals)
        embedding_text = build_embedding_text(record, labels)
        query_vector = Counter(tokenize(embedding_text))
        label_names = {label.label for label in labels}
        risk_concepts = {label.risk_concept for label in labels if label.risk_concept}
        symptom_names = {symptom.name.lower() for symptom in record.symptoms}

        scored: list[tuple[float, list[str], list[str], KnowledgeDocument]] = []
        for document in self.documents:
            semantic_score = cosine_similarity(
                query_vector, self.document_vectors[document.doc_id]
            )
            keyword_matches = symptom_names & document.keywords
            label_matches = label_names & document.labels
            risk_matches = risk_concepts & document.risk_concepts

            score = semantic_score
            score += 0.25 * len(keyword_matches)
            score += 0.35 * len(label_matches)
            score += 0.3 * len(risk_matches)

            sources = []
            if semantic_score > 0:
                sources.append("semantic")
            if keyword_matches:
                sources.append("keyword")
            if label_matches or risk_matches:
                sources.append("symbolic")

            evidence = sorted(keyword_matches | label_matches | risk_matches)
            scored.append((score, sources, evidence, document))

        scored.sort(key=lambda item: item[0], reverse=True)
        results = [
            RetrievalResult(
                rank=index + 1,
                title=document.title,
                condition=document.condition,
                score=round(score, 4),
                retrieval_sources=sources,
                evidence=evidence,
                explanation=_build_explanation(evidence, document),
            )
            for index, (score, sources, evidence, document) in enumerate(scored[:top_k])
            if score > 0
        ]

        return RetrievalBundle(
            record_id=record.record_id,
            patient_id=record.patient_id,
            embedding_text=embedding_text,
            labels=labels,
            results=results,
        )


def _build_explanation(evidence: list[str], document: KnowledgeDocument) -> str:
    if not evidence:
        return f"Matched by semantic similarity to {document.condition} evidence."
    joined = ", ".join(evidence)
    return f"Matched {document.condition} using evidence: {joined}."

