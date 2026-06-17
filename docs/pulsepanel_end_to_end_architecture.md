# PulsePanel — End-to-End Architecture

> **Single source of truth** covering the complete flow from frontend input → orchestration layer → RAG pipeline → databases → ranked response.

---

## 1. High-Level System Flow

```
┌──────────┐     ┌─────────────────────┐     ┌──────────────────────┐     ┌──────────┐
│          │     │                     │     │                      │     │          │
│ Frontend │────▶│  Orchestration      │────▶│  RAG Pipeline        │────▶│ Response │
│ (UI/API) │     │  Layer (12 Tools)   │     │  (3 Databases)       │     │ (JSON)   │
│          │     │                     │     │                      │     │          │
└──────────┘     └─────────────────────┘     └──────────────────────┘     └──────────┘
                        │                              │
                        ▼                              ▼
              ┌──────────────────┐           ┌──────────────────┐
              │  Audit Log       │           │  PostgreSQL      │
              │  (Every Step)    │           │  Qdrant          │
              └──────────────────┘           │  Neo4j           │
                                             └──────────────────┘
```

---

## 2. Data Flow — Step by Step

### Step 1: Frontend Sends Input

The frontend sends a **canonical clinical record** JSON:

```json
{
  "record_id": "REC001",
  "patient_id": "P001",
  "visit_id": "V001",
  "query": "I have severe chest pain and dizziness.",
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

### Step 2: Orchestrator Receives Input

The `PulsePanelOrchestrator.run(raw_input)` method:
1. Creates `OrchestrationContext` with the raw input
2. Executes each tool in dependency order
3. Passes the context through each tool
4. Handles errors with graceful degradation
5. Returns the final `RetrievalBundle`

### Step 3: Pipeline Execution Order

The orchestrator executes tools in sequence. Note: adapters (PostgresAdapter, QdrantAdapter, Neo4jAdapter) are called internally by the tools that need them — they are not separate pipeline steps.

```
Step 1:  InputNormalizer              ──▶ ClinicalRecord (validated)
Step 2:  ClinicalRuleEngine           ──▶ ClinicalLabel[] (derived from vitals)
Step 3:  EmbeddingTextBuilder         ──▶ Embedding text string
Step 4:  PostgresAdapter (optional)   ──▶ Historical context from PostgreSQL
Step 5:  SemanticRetriever            ──▶ Results from Qdrant via QdrantAdapter
Step 6:  KeywordRetriever             ──▶ Results from token-level matching
Step 7:  SymbolicRetriever            ──▶ Results from label/risk matching
Step 8:  GraphRetriever               ──▶ Results from Neo4j via Neo4jAdapter
Step 9:  ResultMerger                 ──▶ Merged + ranked results
Step 10: ExplanationGenerator         ──▶ Results with explanations

Using adapters internally:
  • SemanticRetriever  → calls QdrantAdapter
  • GraphRetriever     → calls Neo4jAdapter
```

### Step 4: Data Written to Databases

#### PostgreSQL (Structured Data)
| Table | What Gets Written |
|---|---|
| `patients` | Patient info (demographics from frontend) |
| `visits` | Visit metadata, query notes, source tags |
| `symptoms` | Symptom name, severity, duration |
| `vitals` | Raw vitals: SpO₂, HR, BP, Temperature |
| `clinical_labels` | Derived labels: hypoxia, tachycardia, rules, evidence |
| `clinical_facts` | Human-readable statements |
| `risk_concepts` | Risk assessments with level & recommendation |
| `canonical_records` | Full normalized JSON record |
| `audit_log` | Every action with old/new values |

#### Qdrant (Vector Store)
| What Gets Stored | Content |
|---|---|
| **Vector embedding** | 384-dim vector from sentence-transformers |
| **Point payload** | `record_id`, `patient_id`, `embedding_text`, `labels[]`, `risk_concepts[]` |

#### Neo4j (Graph Store)
| Node / Edge | Created For |
|---|---|
| `Patient` node | Each unique patient |
| `Symptom` node | Each reported symptom |
| `ClinicalLabel` node | Each derived label |
| `RiskConcept` node | Each identified risk |
| `Condition` node | Knowledge base conditions |
| `HAS_SYMPTOM` edge | Patient → Symptom |
| `HAS_RISK` edge | Patient → RiskConcept |
| `INDICATES` edge | Symptom → Condition |

### Step 5: Retrieval & Ranking

The four retrievers each return results:

```
SemanticRetriever  ──▶ [Result{A: 0.87}, Result{B: 0.72}]
KeywordRetriever   ──▶ [Result{B: 0.65}, Result{C: 0.51}]
SymbolicRetriever  ──▶ [Result{A: 0.90}, Result{D: 0.78}]
GraphRetriever     ──▶ [Result{A: 0.85}, Result{E: 0.60}]
                            │
                            ▼
                    ResultMerger
                            │
                    Deduplicate by doc_id
                    Weighted re-ranking
                    Sort by score
                    Cap at top-k (default 10)
                            │
                            ▼
                    Ranked Results
```

### Step 6: Response Back to Frontend

```json
{
  "record_id": "REC001",
  "patient_id": "P001",
  "embedding_text": "Patient says: I have severe chest pain and dizziness. Patient reports symptoms including chest pain, dizziness. Clinical findings include hypoxia, tachycardia, fever, hypertension. oxygen saturation below normal threshold heart rate is elevated body temperature is high blood pressure is elevated Risk concepts include cardiac risk, respiratory distress.",
  "labels": [
    { "label": "hypoxia", "fact": "oxygen saturation below normal threshold", "rule": "SpO2 < 92", "evidence": {"spo2": 90} },
    { "label": "tachycardia", "fact": "heart rate is elevated", "rule": "HR > 100", "evidence": {"heart_rate": 110} }
  ],
  "results": [
    {
      "rank": 1,
      "title": "Possible acute coronary syndrome",
      "condition": "acs",
      "score": 0.89,
      "retrieval_sources": ["semantic", "symbolic", "graph"],
      "evidence": [
        {"label": "chest pain", "source": "symptom"},
        {"label": "tachycardia", "source": "clinical_rule"}
      ],
      "explanation": "Patient presents with chest pain and tachycardia. Symptoms match acute coronary syndrome criteria. Clinical labels hypoxia and hypertension are consistent with cardiac risk."
    },
    {
      "rank": 2,
      "title": "Possible respiratory distress",
      "condition": "respiratory_distress",
      "score": 0.76,
      "retrieval_sources": ["semantic", "keyword"],
      "evidence": [
        {"label": "hypoxia", "source": "clinical_rule"}
      ],
      "explanation": "Low SpO2 (90) indicates hypoxia. Breathing difficulty matches respiratory distress pattern."
    }
  ]
}
```

---

## 3. Orchestration Layer Architecture

### Core Components

```
pulsepanel_orchestrator/
│
├── orchestrator.py          # PulsePanelOrchestrator — coordinates all tools
├── context.py               # OrchestrationContext — shared data between tools
├── base.py                  # BaseTool — abstract interface for all tools
├── errors.py                # Typed exceptions: ValidationError, ToolError, ConnectionError
├── logging.py               # Audit logging — every step logged with timing
│
├── tools/
│   ├── input_normalizer.py
│   ├── clinical_rule_engine.py
│   ├── embedding_text_builder.py
│   ├── semantic_retriever.py
│   ├── keyword_retriever.py
│   ├── symbolic_retriever.py
│   ├── graph_retriever.py
│   ├── result_merger.py
│   ├── explanation_generator.py
│   └── adapters/
│       ├── base_adapter.py
│       ├── postgres_adapter.py
│       ├── qdrant_adapter.py
│       └── neo4j_adapter.py
│
└── config/
    ├── settings.py           # Configuration from environment
    └── rules.py              # Clinical rule definitions (extensible registry)
```

### Tool Interface

```python
class BaseTool(ABC):
    @property
    def name(self) -> str: ...          # Unique identifier

    @property
    def dependencies(self) -> list[str]: ...  # Tools that must run first

    def run(self, ctx: OrchestrationContext) -> OrchestrationContext: ...
```

### Execution Pipeline (Default Order)

```
Step 1:  InputNormalizer
Step 2:  ClinicalRuleEngine
Step 3:  EmbeddingTextBuilder
Step 4:  PostgresAdapter          (optional — loads historical context)
Step 5:  SemanticRetriever        (via QdrantAdapter)
Step 6:  KeywordRetriever
Step 7:  SymbolicRetriever
Step 8:  GraphRetriever           (via Neo4jAdapter)
Step 9:  ResultMerger
Step 10: ExplanationGenerator
```

Each step is **optional and configurable**. If a DB is down, dependent tools are skipped and partial results are returned.

---

## 4. Database Schema & Model Mapping

### PostgreSQL Tables

| Table | Primary Key | Key Columns | Linked To |
|---|---|---|---|
| `patients` | `patient_id UUID` | name, dob, gender, external_id | — |
| `visits` | `visit_id UUID` | patient_id (FK), visit_date, source[], notes | patients |
| `symptoms` | `symptom_id UUID` | visit_id (FK), name, severity, duration | visits |
| `vitals` | `vital_id UUID` | visit_id (FK), vital_name, value_numeric, unit | visits |
| `lab_reports` | `lab_id UUID` | patient_id (FK), test_name, value, is_abnormal | patients |
| `clinical_labels` | `label_id UUID` | patient_id (FK), label_name, rule_name, evidence JSONB | patients |
| `clinical_facts` | `fact_id UUID` | patient_id (FK), fact_text, source_label_id | clinical_labels |
| `risk_concepts` | `risk_id UUID` | patient_id (FK), concept_name, risk_level, recommendation | patients |
| `fhir_records` | `fhir_id UUID` | patient_id (FK), resource_type, resource_body JSONB | patients |
| `canonical_records` | `record_id UUID` | patient_id (FK), visit_id (FK), record_data JSONB | patients, visits |
| `audit_log` | `audit_id UUID` | action, table_name, old_values JSONB, new_values JSONB | — |
| `clinical_rules` | `rule_id UUID` | rule_name, condition_expr, output_label | — |

### Qdrant Collections

| Collection Name | Payload Fields | Vector Dim |
|---|---|---|
| `clinical_knowledge` | record_id, patient_id, embedding_text, labels[], risk_concepts[] | 384 |

### Neo4j Nodes & Relationships

| Label | Properties | Relationships |
|---|---|---|
| `Patient` | patient_id, name | -[:HAS_SYMPTOM]->Symptom |
| `Symptom` | name, severity, duration | -[:INDICATES]->Condition |
| `Vital` | vital_name, value, unit | -[:TRIGGERS]->ClinicalLabel |
| `ClinicalLabel` | label, rule | -[:IMPLIES]->RiskConcept |
| `RiskConcept` | concept, level | -[:SUGGESTS]->Condition |
| `Condition` | condition, title, doc_id | — |
| `Visit` | visit_id, date, source | -[:RECORDED_AT]->Visit |

### Python Model ↔ Database Mapping

| Python Class | DB Table(s) | Alignment |
|---|---|---|
| `Symptom` | `symptoms` | ✅ Fully aligned |
| `ClinicalRecord` | `patients`, `visits`, `symptoms`, `vitals`, `canonical_records` | ✅ Aligned |
| `ClinicalLabel` | `clinical_labels`, `clinical_facts`, `risk_concepts` | ✅ Aligned |
| `KnowledgeDocument` | No table yet — in-memory | ⚠️ Recommend `knowledge_documents` table |
| `RetrievalResult` | Runtime only — not persisted | 🟡 Optional: log to `audit_log` |
| `RetrievalBundle` | Runtime only — not persisted | 🟡 Optional: store in `canonical_records` |

---

## 5. Error Handling Strategy

| Error Type | Behavior | Example |
|---|---|---|
| **ValidationError** | Halt immediately. Return error to frontend. | Missing patient_id |
| **ToolExecutionError** | Log error, skip tool, continue pipeline. | Embedding model failed |
| **ConnectionError** | Log error, skip dependent tools, return partial results. | Neo4j is down |
| **TimeoutError** | Log timeout, skip tool, continue. | Qdrant query timed out |

**Principle:** Graceful degradation — a single DB failure should not crash clinical triage.

---

## 6. Clinical Rule Engine

### Current Rules (Deterministic)

| Rule | Condition | Output Label | Fact | Risk Concept |
|---|---|---|---|---|
| hypoxia_rule | SpO2 < 92 | hypoxia | oxygen saturation below normal threshold | respiratory distress |
| tachycardia_rule | HR > 100 | tachycardia | heart rate is elevated | cardiac risk |
| fever_rule | Temperature > 37.5°C | fever | body temperature is high | infection risk |
| hypertension_rule | BP systolic ≥ 140 OR diastolic ≥ 90 | hypertension | blood pressure is elevated | cardiac risk |
| bradycardia_rule | HR < 60 | bradycardia | heart rate is below normal | cardiac risk |
| hypotension_rule | BP systolic < 90 | hypotension | blood pressure is below normal | shock risk |
| severe_hypoxia_rule | SpO2 < 85 | severe_hypoxia | oxygen saturation critically low | respiratory failure |

Rules are **extensible** — add new rules to the `clinical_rules` table and the `rules.py` config file.

---

## 7. Auditing & Logging

Every tool call is logged:

```json
{
  "tool": "ClinicalRuleEngine",
  "started_at": "2026-06-17T15:30:00.123Z",
  "duration_ms": 2.3,
  "input_summary": {"vital_count": 5, "record_id": "REC001"},
  "output_summary": {"labels_count": 3, "labels": ["hypoxia", "tachycardia", "fever"]},
  "error": null
}
```

Each retrieval result includes **provenance**:
- Which retrieval path(s) found the document
- Which clinical labels triggered the match
- Which evidence values were used

---

## 8. Implementation Roadmap

### Phase 1 — Core Pipeline (Tools 1–9, no DB dependencies)

| # | Tool | Dependencies | Est. Effort |
|---|---|---|---|
| 1 | InputNormalizer | — | Small |
| 2 | ClinicalRuleEngine | Tool 1 | Small |
| 3 | EmbeddingTextBuilder | Tool 1, 2 | Small |
| 4 | SemanticRetriever | Tool 3 | Medium |
| 5 | KeywordRetriever | Tool 1 | Medium |
| 6 | SymbolicRetriever | Tool 2 | Small |
| 7 | GraphRetriever | Tool 2 | Medium |
| 8 | ResultMerger | Tools 4–7 | Medium |
| 9 | ExplanationGenerator | Tool 8 | Small |
| — | Unit tests for each tool | Each tool | Small each |

### Phase 2 — Database Adapters (Tools 10–12)

| # | Tool | Purpose |
|---|---|---|
| 10 | PostgresAdapter | Read/write structured data |
| 11 | QdrantAdapter | Vector storage & search |
| 12 | Neo4jAdapter | Graph storage & traversal |

### Phase 3 — Integration

| Component | Purpose |
|---|---|
| PulsePanelOrchestrator | Wire all tools together |
| CLI entry point | Test via command line |
| Configuration system | Environment-based settings |
| Integration tests | End-to-end pipeline testing |

---

## 9. Key Design Decisions

| Decision | Rationale |
|---|---|
| **Pure Python (no frameworks)** | Full control, minimal latency, easy debugging, clinically auditable |
| **Tool-per-file architecture** | Single responsibility, easy to test, easy to extend |
| **Context object passing** | Avoids complex function signatures, enables tracing |
| **Graceful degradation** | One DB failure shouldn't halt clinical triage |
| **Deterministic clinical rules** | Same vitals → same labels every time (clinical safety) |
| **Multi-path retrieval** | Combines semantic understanding + exact clinical matching + graph reasoning |
| **Weighted hybrid scoring** | Balances different retrieval strengths |
| **Step-by-step pipeline** | Each step independently testable and auditable |

---

## 10. Architecture Diagram (Complete)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            FRONTEND / API                                    │
│  Sends: ClinicalRecord (JSON)         Receives: RetrievalBundle (JSON)       │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATION LAYER                                   │
│                                                                              │
│  Orchestrator.run(raw_input)                                                 │
│       │                                                                      │
│       ▼                                                                      │
│  ┌──────────────────┐                                                        │
│  │ InputNormalizer  │──► ClinicalRecord (validated)                          │
│  └──────────────────┘                                                        │
│       │                                                                      │
│       ▼                                                                      │
│  ┌──────────────────┐                                                        │
│  │ClinicalRuleEngine│──► ClinicalLabel[] + ClinicalFact[] + RiskConcept[]    │
│  └──────────────────┘                                                        │
│       │                                                                      │
│       ▼                                                                      │
│  ┌──────────────────────┐                                                    │
│  │EmbeddingTextBuilder  │──► Embedding text string                           │
│  └──────────────────────┘                                                    │
│       │                                                                      │
│       ▼                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐           │
│  │                    RETRIEVAL PATHWAYS                          │           │
│  │                                                               │           │
│  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐      │           │
│  │  │   Semantic   │   │   Keyword    │   │  Symbolic    │      │           │
│  │  │  (Qdrant)    │   │  (In-Memory) │   │(Label/Risk)  │      │           │
│  │  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘      │           │
│  │         │                  │                  │              │           │
│  │  ┌──────▼──────────────────▼──────────────────▼───────┐      │           │
│  │  │              Graph (Neo4j)                         │      │           │
│  │  └──────────────────────┬─────────────────────────────┘      │           │
│  └─────────────────────────┼───────────────────────────────────┘           │
│                            │                                               │
│                            ▼                                               │
│  ┌──────────────────┐                                                      │
│  │  ResultMerger    │──► Dedup + Weighted Re-ranking                       │
│  └──────────────────┘                                                      │
│       │                                                                     │
│       ▼                                                                     │
│  ┌──────────────────────┐                                                   │
│  │ExplanationGenerator  │──► RetrievalBundle (with explanations)           │
│  └──────────────────────┘                                                   │
│                                                                              │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATABASE LAYER                                      │
│                                                                              │
│  ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐ │
│  │     PostgreSQL      │   │       Qdrant        │   │       Neo4j         │ │
│  │  (Structured Data)  │   │   (Vector Store)    │   │   (Graph Store)     │ │
│  │                     │   │                     │   │                     │ │
│  │  • patients         │   │  Collection:        │   │  Nodes:             │ │
│  │  • visits           │   │  clinical_knowledge │   │  Patient, Symptom,  │ │
│  │  • symptoms         │   │                     │   │  Vital, Label,      │ │
│  │  • vitals           │   │  • embedding vectors│   │  Risk, Condition    │ │
│  │  • clinical_labels  │   │  • metadata payload │   │                     │ │
│  │  • clinical_facts   │   │                     │   │  Edges:             │ │
│  │  • risk_concepts    │   │                     │   │  HAS_SYMPTOM,       │ │
│  │  • canonical_records│   │                     │   │  INDICATES,         │ │
│  │  • audit_log        │   │                     │   │  IMPLIES, SUGGESTS  │ │
│  └─────────────────────┘   └─────────────────────┘   └─────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 11. File Structure

```
health_panel/
│
├── pulsepanel_orchestrator/          # Orchestration layer (to be built)
│   ├── __init__.py
│   ├── orchestrator.py
│   ├── context.py
│   ├── base.py
│   ├── errors.py
│   ├── logging.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── input_normalizer.py
│   │   ├── clinical_rule_engine.py
│   │   ├── embedding_text_builder.py
│   │   ├── semantic_retriever.py
│   │   ├── keyword_retriever.py
│   │   ├── symbolic_retriever.py
│   │   ├── graph_retriever.py
│   │   ├── result_merger.py
│   │   ├── explanation_generator.py
│   │   └── adapters/
│   │       ├── __init__.py
│   │       ├── base_adapter.py
│   │       ├── postgres_adapter.py
│   │       ├── qdrant_adapter.py
│   │       └── neo4j_adapter.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   └── rules.py
│   └── tests/
│       ├── __init__.py
│       ├── test_input_normalizer.py
│       ├── test_clinical_rule_engine.py
│       ├── test_embedding_text_builder.py
│       ├── test_semantic_retriever.py
│       ├── test_keyword_retriever.py
│       ├── test_symbolic_retriever.py
│       ├── test_graph_retriever.py
│       ├── test_result_merger.py
│       ├── test_explanation_generator.py
│       ├── test_orchestrator.py
│       └── conftest.py
│
├── pulsepanel_rag/                   # Existing RAG prototype (feature branch)
│   ├── __init__.py
│   ├── models.py
│   ├── clinical_rules.py
│   ├── embedding_text.py
│   ├── retrieval.py
│   ├── mock_data.py
│   └── demo.py
│
├── docker/
│   └── postgres/
│       └── init.sql
│
├── docs/
│   ├── Pulsepanel_clinical_graphrag_architecture.md     # Data architecture
│   ├── pulsepanel_orchestration_layer.md                # Orchestration design
│   └── pulsepanel_end_to_end_architecture.md            ← THIS DOCUMENT
│
├── scripts/
│   └── start-dbs.sh
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 12. Summary

The PulsePanel system processes clinical data through a **pure Python tool-based pipeline**:

1. **Frontend** sends a canonical clinical record (JSON)
2. **Orchestration Layer** executes 12 specialized tools in sequence
3. **Database Layer** persists data to PostgreSQL, Qdrant, and Neo4j
4. **Retrieval** uses 4 parallel paths: semantic, keyword, symbolic, and graph
5. **Results** are merged, ranked, explained, and returned to the frontend

The system prioritizes **accuracy over speed**, uses **deterministic clinical rules** for safety, and maintains **full auditability** for healthcare compliance.
