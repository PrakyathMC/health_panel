# PulsePanel Clinical Data Architecture

## 1. Purpose
PulsePanel is not just a place to store patient records. It is a system for building a **Clinical Knowledge Graph + Vector Index + Structured Store** from multiple healthcare sources.

The goal is to make clinical data:
- easy to search
- easy to filter
- easy to connect
- easy to explain
- safe to audit

---

## 2. Why this architecture is needed
Healthcare data comes in different forms:
- patient symptoms in text
- doctor notes in text
- vitals as numbers
- lab reports as structured values
- historical records as context
- wearable readings as live measurements

A single JSON document is not enough because:
- numbers need exact filtering
- text needs semantic search
- relationships need graph links
- clinical decisions need explanations

So PulsePanel uses three storage layers:
- **Structured Store** for exact values
- **Vector Store** for semantic search
- **Graph Store** for relationships

---

## 3. Types of data in the system

### 3.1 Raw textual data
This is the original text from a patient or doctor.

Examples:
- "I have chest pain and dizziness."
- "Patient presents with tachycardia and possible ACS."

Use:
- symptom extraction
- clinical meaning
- semantic search

---

### 3.2 Raw numerical data
This is measured data from vitals, wearables, or devices.

Examples:
- SpO₂ = 90
- HR = 110
- BP = 140/90
- Temperature = 38.1

Use:
- threshold checks
- clinical rules
- risk scoring
- exact filtering

Raw numbers should be stored as they are, but they should not be the main embedding input.

---

### 3.3 Clinical labels
These are meaningful labels created from raw numbers.

Examples:
- hypoxia
- tachycardia
- fever
- hypertension

Use:
- semantic search
- graph nodes
- patient context
- embeddings

---

### 3.4 Clinical facts
These are short human-readable statements derived from labels.

Examples:
- oxygen saturation below normal threshold
- heart rate is elevated
- body temperature is high

Use:
- better embeddings
- better explanations
- better retrieval quality

---

### 3.5 Risk concepts
These are higher-level clinical meanings.

Examples:
- respiratory distress
- cardiac risk
- sepsis risk

Use:
- triage reasoning
- graph traversal
- care recommendations

---

## 4. Why raw numbers are not embedded directly
Embedding models understand meaning better than numbers.

For example:
- `SpO₂ = 90`
- `SpO₂ = 75`
- `SpO₂ = 98`

These values are clinically very different, but a model may not understand that difference well if only the raw numbers are embedded.

That is why PulsePanel converts numbers into labels first.

Example:
- `SpO₂ = 90` → `hypoxia`
- `HR = 110` → `tachycardia`

Then the embedding text becomes something like:
- "Patient has hypoxia and tachycardia."

This gives much better semantic search.

---

## 5. How labels are created from numerical vitals
Labels should be generated using **deterministic clinical rules**, not by guessing.

### Example rules
- SpO₂ < 92 → hypoxia
- HR > 100 → tachycardia
- Temperature > 37.5 → fever
- BP ≥ 140/90 → hypertension

This is important because it keeps the system:
- consistent
- explainable
- auditable
- clinically safer

---

## 6. Multi-level transformation of data
PulsePanel should transform data in layers.

### Layer 1: Raw measurement
Example:
- SpO₂ = 90

### Layer 2: Clinical label
Example:
- hypoxia

### Layer 3: Clinical fact
Example:
- oxygen saturation below normal threshold

### Layer 4: Risk concept
Example:
- respiratory distress

### Layer 5: Recommendation
Example:
- urgent evaluation recommended

This layering helps the system reason step by step.

---

## 7. Data sources
PulsePanel can take input from many sources.

### 7.1 Patient
Gives symptoms in simple language.

Why:
- describes how the person feels
- provides subjective symptoms

---

### 7.2 Doctor
Gives clinical notes and diagnoses.

Why:
- includes medical judgment
- may contain differential diagnosis
- is more precise clinically

---

### 7.3 Wearables
Gives live vitals like SpO₂ and HR.

Why:
- provides real-time monitoring
- helps detect worsening condition

---

### 7.4 EHR / FHIR
Gives past medical history and structured records.

Why:
- adds context
- supports continuity of care

---

### 7.5 Lab reports
Gives objective diagnostic values.

Why:
- supports stronger clinical evidence
- helps improve triage and risk assessment

---

## 8. Canonical clinical record
All source data should be converted into one normalized structure.

Example:

```json
{
  "record_id": "REC001",
  "patient_id": "P001",
  "source": ["patient", "doctor", "wearable"],
  "symptoms": [
    {
      "name": "chest pain",
      "duration": "2 hours",
      "severity": "severe"
    },
    {
      "name": "dizziness"
    }
  ],
  "vitals": {
    "SpO2": 90,
    "HR": 110,
    "BP": "140/90"
  },
  "clinical_categories": ["hypoxia", "tachycardia", "hypertension"]
}
```

This canonical form makes all data sources consistent.

---

## 9. Where each type of data should be stored

### 9.1 PostgreSQL
Store:
- raw vitals
- symptoms
- lab values
- patient history
- visit records
- clinical labels
- clinical scores

Why:
- exact filtering
- structured queries
- source of truth
- audit support

---

### 9.2 Qdrant or other vector database
Store:
- embedding text
- clinical summaries
- symptom narratives
- derived clinical facts

Why:
- semantic search
- query similarity
- retrieval by meaning

---

### 9.3 Neo4j or other graph database
Store:
- patient nodes
- symptom nodes
- vital nodes
- risk nodes
- condition nodes
- relationship edges

Why:
- connect clinical entities
- support GraphRAG
- explain relations between findings

---

## 10. Storage responsibility matrix

| Data type | PostgreSQL | Vector DB | Graph DB |
|---|---:|---:|---:|
| Raw vitals | Yes | No | Optional |
| Symptoms | Yes | Yes | Yes |
| Clinical labels | Yes | Yes as metadata | Yes |
| Clinical facts | Optional | Yes | Yes |
| Risk concepts | Optional | Yes | Yes |
| Embeddings | No | Yes | No |
| Relationships | No | No | Yes |
| FHIR records | Yes | No | No |

---

## 11. How embeddings should be generated
Embeddings should be created from **text that contains clinical meaning**, not from raw numbers alone.

### Good embedding text
- "Patient has chest pain, hypoxia, and tachycardia."
- "Findings suggest respiratory distress and urgent evaluation."

### Weak embedding text
- "SpO₂ 90, HR 110, BP 140/90"

The good version is better because it carries medical meaning.

---

## 12. Why labeling helps embeddings
Labels convert numbers into language that embedding models understand better.

Example:
- SpO₂ = 90 → hypoxia
- HR = 110 → tachycardia

Now the vector database can match queries like:
- low oxygen
- shortness of breath
- fast pulse
- breathing difficulty

This is the main reason labels are needed.

---

## 13. Query handling approach
PulsePanel should support three types of retrieval.

### 13.1 Symbolic retrieval
Uses exact conditions.

Example:
- SpO₂ < 92
- HR > 100

Why:
- exact clinical filtering
- safe threshold checks

---

### 13.2 Semantic retrieval
Uses meaning from text and labels.

Example query:
- "breathing difficulty with low oxygen"

Why:
- matches similar clinical language
- works even if wording is different

---

### 13.3 Graph retrieval
Uses relationships between entities.

Example:
- chest pain → hypoxia → ACS

Why:
- gives context
- supports explainability
- improves clinical reasoning

---

## 14. HyDE retrieval
HyDE means generating a hypothetical clinical document from the user query before searching.

### Example query
- "shortness of breath with low oxygen"

### Hypothetical document
- "Patient presents with shortness of breath, hypoxia, and possible respiratory distress."

Why it helps:
- improves recall
- helps vague queries
- turns a short query into richer clinical language

---

## 15. How all data is connected
All stored data should share a common identifier.

Example identifiers:
- patient_id
- visit_id
- record_id
- encounter_id

These IDs should be used across:
- PostgreSQL
- Vector DB
- Graph DB

This is how all sources stay connected.

---

## 16. Example graph structure

### Nodes
- Patient
- Symptom
- Vital
- Risk
- Condition
- Visit
- Doctor

### Example relationships
- Patient has symptom Chest Pain
- Patient has vital SpO₂ = 90
- Patient has risk Hypoxia
- Patient possible condition ACS

This graph structure makes the system easier to explain and retrieve from.

---

## 17. Auditability and explainability
Every label should have a reason.

Example:

```json
{
  "label": "hypoxia",
  "source": "clinical_rule",
  "rule": "SpO2 < 92",
  "evidence": {
    "SpO2": 90
  }
}
```

Why this matters:
- clinicians need traceability
- debugging becomes easier
- system decisions can be reviewed

---

## 18. End-to-end flow

1. User provides symptoms, notes, or vitals.
2. Data is extracted and normalized.
3. Raw vitals are stored as structured values.
4. Clinical labels are generated from rules.
5. Clinical facts and risk concepts are created.
6. Embedding text is built from meaningful text.
7. Embeddings are stored in the vector database.
8. Entities and links are stored in the graph database.
9. Queries use symbolic, semantic, and graph retrieval together.
10. Final output is ranked and explained.

---

## 19. Why this design is better than one JSON blob
A single JSON record is simple, but it becomes hard to use later.

Problems with one blob:
- hard to filter precisely
- hard to update one part
- hard to search semantically
- hard to connect data across sources
- hard to explain results

This design solves those problems by separating:
- structure
- meaning
- relationships

---

## 20. Final summary
PulsePanel should store clinical data in three connected layers:

- **Structured data** for exact values and rules
- **Vector data** for semantic search
- **Graph data** for relationships and reasoning

Raw vitals should stay numeric for filtering and auditing.

Clinical labels should be created from those numbers using clear rules.

Embeddings should be created from symptoms, labels, and clinical meaning, not from raw numbers alone.

This is what makes the system accurate, explainable, and suitable for healthcare GraphRAG use.

---

## 21. Python Model ↔ PostgreSQL Schema Mapping

This section provides a field-by-field mapping between the Python dataclasses (defined in `pulsepanel_rag/models.py` on the `feature/retrieval-mechanincs` branch) and the PostgreSQL schema (defined in `docker/postgres/init.sql`).

This is the **single source of truth** connecting the orchestration layer's in-memory data structures to their persisted storage.

---

### 21.1 `Symptom` ↔ `symptoms` table

| Python Field | DB Column | Match | Notes |
|---|---|---|---|
| `name: str` | `name VARCHAR(255)` | ✅ Direct | — |
| `severity: str \| None` | `severity VARCHAR(50)` | ✅ Direct | Optional in both |
| `duration: str \| None` | `duration VARCHAR(100)` | ✅ Direct | Optional in both |
| *—infra—* | `symptom_id UUID PK` | 🔧 Auto | Generated by DB |
| *—infra—* | `visit_id UUID FK` | 🔧 Set by orchestrator | Links to `visits` |
| *—infra—* | `patient_id UUID FK` | 🔧 Set by orchestrator | Links to `patients` |
| *—infra—* | `source VARCHAR(50)` | 🔧 Set by orchestrator | From `ClinicalRecord.source` |
| *—infra—* | `recorded_at TIMESTAMPTZ` | 🔧 Auto | Generated by DB |

**Verdict:** ✅ Fully compatible. Infrastructure fields (IDs, timestamps) are set automatically by the orchestrator or database.

---

### 21.2 `ClinicalRecord` ↔ `patients` + `visits` + `symptoms` + `vitals` + `canonical_records`

`ClinicalRecord` is the **primary input model** — it maps to **5 tables** when persisted.

| Python Field | DB Location | Match | Notes |
|---|---|---|---|
| `record_id: str` | `canonical_records.record_id` | ✅ Direct | Canonical JSON view |
| `patient_id: str` | `patients.patient_id` | ✅ Direct | Also FK in all child tables |
| `visit_id: str \| None` | `visits.visit_id` | ✅ Direct | Auto-generated if None |
| `query: str` | `visits.notes` | ⚠️ Indirect | Or stored in `canonical_records.record_data->>query` |
| `symptoms: list[Symptom]` | `symptoms` table | ✅ Direct | One row per symptom |
| `vitals: dict[str, float \| str]` | `vitals` table | ✅ Transformed | Each key → `vital_name`, value → `value_numeric` or `value_text` |
| `source: list[str]` | `visits.source TEXT[]` | ✅ Direct | PostgreSQL text array |
| *—not in model—* | `patients.name` | ⚠️ Gap | Patient name not in ClinicalRecord |
| *—not in model—* | `patients.date_of_birth` | ⚠️ Gap | Patient DOB not in model |
| *—not in model—* | `patients.gender` | ⚠️ Gap | Patient gender not in model |
| *—not in model—* | `patients.external_id` | ⚠️ Gap | EHR/FHIR external ID not in model |
| *—not in model—* | `visits.visit_date` | ⚠️ Gap | Visit timestamp not in model |

**Verdict:** ⚠️ Partially compatible. Patient demographics (name, DOB, gender) exist in schema but not in `ClinicalRecord` — they would either need to be added or stored via FHIR records. The `query` field needs a designated column.

---

### 21.3 `ClinicalLabel` ↔ `clinical_labels` + `clinical_facts` + `risk_concepts`

`ClinicalLabel` is a composite model — its fields map to **3 separate tables**.

| Python Field | DB Location | Match | Notes |
|---|---|---|---|
| `label: str` | `clinical_labels.label_name` | ✅ Direct | — |
| `fact: str` | `clinical_facts.fact_text` | ✅ Split | Stored in separate table |
| `risk_concept: str \| None` | `risk_concepts.concept_name` | ✅ Split | Stored in separate table |
| `rule: str` | `clinical_labels.rule_name` | ✅ Direct | — |
| `evidence: dict[str, float \| str]` | `clinical_labels.evidence JSONB` | ✅ Direct | JSONB matches dict perfectly |
| *—not in model—* | `risk_concepts.risk_level` | ⚠️ Gap | e.g. "low", "moderate", "high" |
| *—not in model—* | `risk_concepts.recommendation` | ⚠️ Gap | e.g. "urgent evaluation recommended" |
| *—not in model—* | `clinical_labels.is_active` | 🔧 Defaults TRUE | Can default TRUE |
| *—infra—* | `clinical_labels.source` | 🔧 Set to "clinical_rule" | Deterministic |

**Verdict:** ⚠️ Partially compatible. The `risk_level` and `recommendation` fields exist in the DB schema but not in the Python model. These can either be added to `ClinicalLabel` or derived differently.

---

### 21.4 `KnowledgeDocument` — No PostgreSQL table exists

This is the **reference knowledge base** used for retrieval. Currently it exists only as **in-memory mock data** (`pulsepanel_rag/mock_data.py`).

| Python Field | DB Location | Match | Notes |
|---|---|---|---|
| `doc_id: str` | ❌ No table | ❌ Missing | Needs a `knowledge_documents` table |
| `title: str` | ❌ No table | ❌ Missing | — |
| `condition: str` | ❌ No table | ❌ Missing | — |
| `text: str` | ❌ No table | ❌ Missing | — |
| `keywords: set[str]` | ❌ No table | ❌ Missing | Could be JSONB array |
| `labels: set[str]` | ❌ No table | ❌ Missing | — |
| `risk_concepts: set[str]` | ❌ No table | ❌ Missing | — |

**Recommendation:** Create a `knowledge_documents` table with JSONB fields for `keywords`, `labels`, and `risk_concepts` sets. This knowledge base feeds into Qdrant (for embeddings) and Neo4j (for graph relationships).

---

### 21.5 `RetrievalResult` — Runtime output, no DB table

| Python Field | Purpose |
|---|---|
| `rank: int` | Position in ranked results |
| `title: str` | Knowledge document title |
| `condition: str` | Matched clinical condition |
| `score: float` | Hybrid retrieval score |
| `retrieval_sources: list[str]` | Which paths found it (semantic, keyword, symbolic, graph) |
| `evidence: list[dict]` | Evidence dicts per match |
| `explanation: str` | Human-readable explanation |

**Verdict:** 🟡 Runtime data structure. Not directly persisted, but could be stored in `canonical_records.record_data` or an `audit_log` entry for traceability.

---

### 21.6 `RetrievalBundle` — Runtime output, no DB table

| Python Field | Purpose |
|---|---|
| `record_id: str` | Links back to input record |
| `patient_id: str` | Links back to patient |
| `embedding_text: str` | Text used for embedding generation |
| `labels: list[ClinicalLabel]` | All derived clinical labels |
| `results: list[RetrievalResult]` | Ranked retrieval results |

**Verdict:** 🟡 Runtime data structure. The `embedding_text` and derived labels are already persisted in earlier steps. The `results` could be persisted to a `retrieval_results` table or logged to `audit_log` for auditability.

---

### 21.7 Summary of Gaps & Recommendations

| # | Gap | Impact | Recommendation |
|---|---|---|---|
| 1 | `ClinicalRecord` missing patient demographics | Cannot populate `patients.name`, `date_of_birth`, `gender` | Add fields to `ClinicalRecord` OR use FHIR records as source |
| 2 | `ClinicalRecord.query` has no dedicated column | Query text lost if not stored | Add `query TEXT` column to `visits` table |
| 3 | `ClinicalLabel.risk_level` and `recommendation` missing | `risk_concepts` table has these but model doesn't | Add optional fields to `ClinicalLabel` |
| 4 | `KnowledgeDocument` has no DB table | Knowledge base is in-memory only | Add `knowledge_documents` table to PostgreSQL |
| 5 | No `retrieval_results` table | Retrieval output not persisted | Optional — can log to `audit_log` or store in `canonical_records` |

### 21.8 Recommended Schema Addition — `knowledge_documents`

```sql
CREATE TABLE knowledge_documents (
    doc_id          VARCHAR(255) PRIMARY KEY,
    title           VARCHAR(500) NOT NULL,
    condition       VARCHAR(500),
    doc_text        TEXT NOT NULL,
    keywords        TEXT[],
    labels          TEXT[],
    risk_concepts   TEXT[],
    embedding       VECTOR(384),      -- if pgvector is enabled
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

This bridges the gap between the in-memory `MOCK_KNOWLEDGE_BASE` and a persisted knowledge base that can be indexed in both Qdrant and Neo4j.

