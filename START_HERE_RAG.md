# PulsePanel RAG Branch Starter

Your branch owns the retrieval layer. Build it behind clear contracts so the
frontend/data and orchestration/DB teammates can work in parallel.

## Input Contract

The frontend/data layer should send a canonical clinical record:

```json
{
  "record_id": "REC001",
  "patient_id": "P001",
  "visit_id": "V001",
  "query": "I have chest pain and dizziness",
  "symptoms": [
    { "name": "chest pain", "severity": "severe", "duration": "2 hours" },
    { "name": "dizziness" }
  ],
  "vitals": {
    "spo2": 90,
    "heart_rate": 110,
    "temperature_c": 38.1,
    "systolic_bp": 145,
    "diastolic_bp": 92
  },
  "source": ["patient", "wearable"]
}
```

## Output Contract

The orchestrator should receive a ranked retrieval bundle:

```json
{
  "record_id": "REC001",
  "patient_id": "P001",
  "embedding_text": "Patient reports chest pain and dizziness. Clinical findings include hypoxia, tachycardia, fever, hypertension.",
  "labels": [
    {
      "label": "hypoxia",
      "rule": "spo2 < 92",
      "evidence": { "spo2": 90 }
    }
  ],
  "results": [
    {
      "rank": 1,
      "title": "Possible acute coronary syndrome",
      "score": 0.81,
      "retrieval_sources": ["semantic", "keyword", "symbolic"],
      "evidence": ["chest pain", "tachycardia", "hypertension"],
      "explanation": "Matched severe chest pain with elevated heart rate and blood pressure."
    }
  ]
}
```

## Your Build Order

1. Normalize input into the canonical shape.
2. Convert raw vitals into deterministic labels and audit evidence.
3. Generate embedding text from symptoms, labels, and clinical facts.
4. Ingest records into a vector store.
5. Retrieve through semantic, keyword, and symbolic paths.
6. Merge and rank results for the orchestration teammate.
7. Add Qdrant/Postgres/Neo4j adapters once teammate contracts stabilize.

## Current Local Prototype

This repo includes a dependency-light prototype in `pulsepanel_rag/`:

- `models.py`: shared request/response dataclasses.
- `clinical_rules.py`: deterministic vital-to-label rules.
- `embedding_text.py`: clinically meaningful text builder.
- `retrieval.py`: in-memory hybrid retriever for local development.
- `mock_data.py`: tiny seed knowledge base.
- `demo.py`: runnable example.

Run:

```powershell
python -m pulsepanel_rag.demo
```

