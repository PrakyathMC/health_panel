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

