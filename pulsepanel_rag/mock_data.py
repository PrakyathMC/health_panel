from __future__ import annotations

from .models import KnowledgeDocument


MOCK_KNOWLEDGE_BASE = [
    KnowledgeDocument(
        doc_id="condition_acs",
        title="Possible acute coronary syndrome",
        condition="acute coronary syndrome",
        text=(
            "Chest pain with dizziness, tachycardia, hypertension, or shortness of "
            "breath can indicate cardiac risk and possible acute coronary syndrome."
        ),
        keywords={"chest pain", "dizziness", "shortness of breath"},
        labels={"tachycardia", "hypertension"},
        risk_concepts={"cardiac risk", "cardiovascular risk"},
    ),
    KnowledgeDocument(
        doc_id="condition_respiratory_distress",
        title="Possible respiratory distress",
        condition="respiratory distress",
        text=(
            "Low oxygen saturation, hypoxia, shortness of breath, and rapid heart "
            "rate can indicate respiratory distress requiring urgent evaluation."
        ),
        keywords={"shortness of breath", "breathing difficulty", "low oxygen"},
        labels={"hypoxia", "tachycardia"},
        risk_concepts={"respiratory distress"},
    ),
    KnowledgeDocument(
        doc_id="condition_infection",
        title="Possible infection or sepsis risk",
        condition="infection",
        text=(
            "Fever with tachycardia, weakness, confusion, or abnormal vitals can "
            "indicate infection risk or possible sepsis risk."
        ),
        keywords={"fever", "weakness", "confusion"},
        labels={"fever", "tachycardia"},
        risk_concepts={"infection risk"},
    ),
]

