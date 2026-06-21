"""Centralized clinical knowledge base.

Single source of truth for all retrieval tools. Every retriever imports from
here instead of duplicating the data.
"""

from __future__ import annotations

from ..models import KnowledgeDocument

# ---------------------------------------------------------------------------
# Built-in knowledge documents (Phase 1 — in-memory)
# ---------------------------------------------------------------------------
# In Phase 2 these will be replaced by Qdrant/Neo4j queries, but the
# data model remains the same.

KNOWLEDGE_DOCUMENTS: list[KnowledgeDocument] = [
    KnowledgeDocument(
        doc_id="kb_acs",
        title="Possible acute coronary syndrome",
        condition="acs",
        text="Acute coronary syndrome (ACS) encompasses unstable angina and myocardial infarction. "
        "Common presentations include chest pain, shortness of breath, diaphoresis, and dizziness. "
        "Risk factors include hypertension, tachycardia, and hypoxia.",
        keywords=["chest pain", "dizziness", "shortness of breath", "sweating", "nausea"],
        labels=["hypoxia", "tachycardia", "hypertension"],
        risk_concepts=["cardiac risk"],
    ),
    KnowledgeDocument(
        doc_id="kb_respiratory",
        title="Possible respiratory distress",
        condition="respiratory_distress",
        text="Respiratory distress can result from pneumonia, COPD exacerbation, pulmonary embolism, "
        "or heart failure. Key indicators include low oxygen saturation, tachypnea, and use of "
        "accessory muscles. Urgent evaluation of oxygenation and ventilation is required.",
        keywords=["shortness of breath", "wheezing", "cough", "low oxygen", "breathing difficulty"],
        labels=["hypoxia", "tachypnea", "severe_hypoxia"],
        risk_concepts=["respiratory distress", "respiratory failure"],
    ),
    KnowledgeDocument(
        doc_id="kb_infection",
        title="Possible infection or sepsis risk",
        condition="infection",
        text="Infections can range from localised to systemic (sepsis). Signs include fever, "
        "tachycardia, hypotension, and altered mental status. Early recognition and treatment "
        "with appropriate antibiotics improve outcomes significantly.",
        keywords=["fever", "chills", "confusion", "infection", "sepsis", "warm skin"],
        labels=["fever", "tachycardia", "hypotension"],
        risk_concepts=["infection risk", "shock risk"],
    ),
]

# Convenience lookup
KNOWLEDGE_BY_ID: dict[str, KnowledgeDocument] = {
    doc.doc_id: doc for doc in KNOWLEDGE_DOCUMENTS
}

# Label → condition mapping (for GraphRetriever)
LABEL_TO_CONDITION: dict[str, list[tuple[str, str]]] = {
    "hypoxia": [("kb_respiratory", "respiratory distress"), ("kb_acs", "cardiac risk")],
    "severe_hypoxia": [("kb_respiratory", "respiratory failure")],
    "tachycardia": [("kb_acs", "cardiac risk"), ("kb_infection", "infection risk")],
    "bradycardia": [("kb_acs", "cardiac risk")],
    "fever": [("kb_infection", "infection risk")],
    "hypertension": [("kb_acs", "cardiac risk")],
    "hypotension": [("kb_infection", "shock risk")],
    "tachypnea": [("kb_respiratory", "respiratory distress")],
}

RISK_TO_CONDITION: dict[str, list[tuple[str, str]]] = {
    "cardiac risk": [("kb_acs", "Possible acute coronary syndrome")],
    "respiratory distress": [("kb_respiratory", "Possible respiratory distress")],
    "respiratory failure": [("kb_respiratory", "Possible respiratory distress")],
    "infection risk": [("kb_infection", "Possible infection or sepsis risk")],
    "shock risk": [("kb_infection", "Possible infection or sepsis risk")],
    "exposure risk": [],
}
