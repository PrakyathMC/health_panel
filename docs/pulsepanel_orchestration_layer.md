# PulsePanel Orchestration Layer — Design Document

> **Philosophy:** Accuracy over speed. Pure Python. No frameworks. Each tool does one thing well.

---

## 1. Why No Frameworks?

Frameworks like LangChain, LlamaIndex, Haystack add:
- Unnecessary abstraction layers → debugging nightmare
- Opaque prompt/chain management → hard to audit clinically
- Hidden latency from serialization, callbacks, plugin systems
- Dependency bloat → harder to certify for healthcare use

**Pure Python** gives us:
- Full control over every millisecond
- Complete auditability — every step logs what it did
- Minimal attack surface
- Trivial debugging — `pdb` through the entire pipeline
- Easy to test each tool in isolation

---

## 2. Architecture Overview

```
┌───────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                           │
│  Coordinates tool execution, error handling, logging      │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐              │
│  │  Tool 1  │ → │  Tool 2  │ → │  Tool 3  │  ...         │
│  │Normalize │   │  Rules   │   │ Embedding│              │
│  └──────────┘   └──────────┘   └──────────┘              │
│       │              │              │                     │
│       ▼              ▼              ▼                     │
│  ┌─────────────────────────────────────┐                  │
│  │           RETRIEVAL TOOLS           │                  │
│  │  ┌──────┐  ┌───────┐  ┌─────────┐  │                  │
│  │  │Semantic│ │Keyword│  │ Symbolic│  │                  │
│  │  └──────┘  └───────┘  └─────────┘  │                  │
│  └─────────────────────────────────────┘                  │
│       │              │              │                     │
│       ▼              ▼              ▼                     │
│  ┌──────────┐   ┌──────────┐                              │
│  │  Merger  │ → │Explainer│                              │
│  └──────────┘   └──────────┘                              │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

---

## 3. Tool Catalog

Each tool is a **pure Python class** with a single `run(context)` method.
- **Input:** A shared `OrchestrationContext` dataclass (immutable during flight — tools add to it)
- **Output:** The tool writes its results back into the context
- **Error handling:** Tools raise typed exceptions — the orchestrator catches them

### Tool 1 — `InputNormalizer`
**Purpose:** Validate and normalize the raw clinical input into canonical form.

```
Input:  Raw dict/JSON
Output: Cleaned ClinicalRecord

Responsibilities:
- Validate required fields (record_id, patient_id, query, vitals)
- Normalize vital names (spo2 → SpO2, heart_rate → HR)
- Parse symptom durations into standard format
- Reject malformed input with explicit error messages
```

### Tool 2 — `ClinicalRuleEngine`
**Purpose:** Derive deterministic clinical labels from raw vitals.

```
Input:  ClinicalRecord (vitals)
Output: List[ClinicalLabel]

Responsibilities:
- Apply threshold rules (SpO2 < 92 → hypoxia)
- Attach evidence (which vital value triggered the rule)
- Attach clinical facts and risk concepts
- Deterministic — same vitals always produce same labels

Rules (extensible via registry):
├── hypoxia:       SpO2 < 92
├── tachycardia:   HR > 100
├── fever:         Temp > 37.5°C
├── hypertension:  BP ≥ 140/90
├── bradycardia:   HR < 60
├── hypotension:   BP < 90/60
├── tachypnea:     RR > 20
├── hypothermia:   Temp < 35.0°C
```

### Tool 3 — `EmbeddingTextBuilder`
**Purpose:** Build rich clinical text from record + labels for vector search.

```
Input:  ClinicalRecord + List[ClinicalLabel]
Output: Embedding text string

Responsibilities:
- Combine patient query, symptoms, and clinical labels
- Format as natural clinical language
- Preserve clinical meaning for semantic search
```

### Tool 4 — `SemanticRetriever`
**Purpose:** Search the vector store (Qdrant) using embedding similarity.

```
Input:  Embedding text
Output: List[RetrievalResult] (from vector similarity)

Responsibilities:
- Generate embedding from embedding text
- Query Qdrant collection for top-k similar documents
- Return results with similarity scores
```

### Tool 5 — `KeywordRetriever`
**Purpose:** Search using token-level keyword matching.

```
Input:  ClinicalRecord symptoms + labels
Output: List[RetrievalResult] (from keyword overlap)

Responsibilities:
- Tokenize symptoms and labels
- Match against knowledge base keywords
- Score by overlap ratio
```

### Tool 6 — `SymbolicRetriever` (Label/Risk Graph)
**Purpose:** Search using exact label and risk-concept matching.

```
Input:  List[ClinicalLabel]
Output: List[RetrievalResult] (from label/risk matching)

Responsibilities:
- Match clinical labels against document labels
- Match risk concepts against document risk_concepts
- Score by exact match count
```

### Tool 7 — `GraphRetriever` (Neo4j)
**Purpose:** Traverse the clinical knowledge graph.

```
Input:  ClinicalRecord entities + labels
Output: List[RetrievalResult] (from graph traversal)

Responsibilities:
- Connect patient symptoms to condition nodes
- Traverse edges: Symptom → Risk → Condition
- Return related knowledge documents
```

### Tool 8 — `ResultMerger`
**Purpose:** Merge, deduplicate, and rank results from all retrieval paths.

```
Input:  List[List[RetrievalResult]] (from multiple retrievers)
Output: Merged + ranked List[RetrievalResult]

Algorithm:
1. Collect all results from all paths
2. Deduplicate by doc_id (keep highest score)
3. Weighted re-ranking:
   - Semantic + Keyword + Symbolic from HybridRetriever (current weights)
   - Graph results get additional boost
4. Sort by final score descending
5. Cap at top-k (configurable, default 10)
```

### Tool 9 — `ExplanationGenerator`
**Purpose:** Generate human-readable explanations for each result.

```
Input:  RetrievalResult + context (which tools contributed)
Output: RetrievalResult with populated explanation field

Responsibilities:
- Explain why each document matched
- Include which clinical labels triggered the match
- Include which retrieval path(s) found it
- Format in clear clinical language
```

### Tool 10 — `PostgresAdapter`
**Purpose:** Read/write structured clinical data from PostgreSQL.

```
Input:  ClinicalRecord + operation (read/write/query)
Output: Requested data

Responsibilities:
- Store clinical records in structured tables
- Query by patient_id, visit_id, record_id
- Retrieve historical records for context
```

### Tool 11 — `QdrantAdapter`
**Purpose:** Manage vector storage and retrieval in Qdrant.

```
Input:  Embedding text + operation (ingest/search/delete)
Output: Query results or ingestion confirmation

Responsibilities:
- Generate embeddings via OpenAI text-embedding-3-large API
- Ingest embedding text + metadata into Qdrant collection
- Search by embedding vector
- Filter by metadata (patient_id, visit_id)
```

### Tool 12 — `Neo4jAdapter`
**Purpose:** Manage graph storage and traversal in Neo4j.

```
Input:  Clinical entities + operation (store/traverse/query)
Output: Graph traversal results

Responsibilities:
- Create patient, symptom, label, condition nodes
- Create relationships between nodes
- Traverse from symptoms → risk → conditions
- Support explainability queries
```

---

## 4. Orchestrator Design

The `Orchestrator` is the central coordinator. It:

```python
class PulsePanelOrchestrator:
    """
    Coordinates the execution of all RAG pipeline tools.
    
    - Maintains tool registry (extensible)
    - Executes tools in dependency order
    - Handles errors with graceful degradation
    - Logs every step for auditability
    - Returns final RetrievalBundle
    """
    
    def __init__(self, tools: list[BaseTool]):
        self.tools = {t.name: t for t in tools}
    
    def run(self, raw_input: dict) -> RetrievalBundle:
        context = OrchestrationContext(raw_input)
        for step in self._pipeline:
            tool = self.tools[step.tool_name]
            context = tool.run(context)
        return context.bundle
```

### Execution Pipeline (Default Sequence)

```
Step 1:  InputNormalizer        → validates & normalizes
Step 2:  ClinicalRuleEngine     → derives clinical labels
Step 3:  EmbeddingTextBuilder   → builds embedding text
Step 4:  PostgresAdapter         → loads additional context (optional)
Step 5:  SemanticRetriever       → vector search (via QdrantAdapter)
Step 6:  KeywordRetriever        → token-level search
Step 7:  SymbolicRetriever       → label/risk match
Step 8:  GraphRetriever          → graph traversal (via Neo4jAdapter)
Step 9:  ResultMerger            → merge & rank
Step 10: ExplanationGenerator    → explain results
```

Each step is **optional and configurable** — if Qdrant isn't available, skip SemanticRetriever.

---

## 5. Data Flow

### Context Object

```python
@dataclass
class OrchestrationContext:
    raw_input: dict                              # Original input
    record: ClinicalRecord | None = None         # Normalized record
    labels: list[ClinicalLabel] | None = None    # Derived labels
    embedding_text: str | None = None            # Embedding text
    semantic_results: list[RetrievalResult] = field(default_factory=list)
    keyword_results: list[RetrievalResult] = field(default_factory=list)
    symbolic_results: list[RetrievalResult] = field(default_factory=list)
    graph_results: list[RetrievalResult] = field(default_factory=list)
    merged_results: list[RetrievalResult] = field(default_factory=list)
    bundle: RetrievalBundle | None = None        # Final output
    errors: list[ToolError] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)  # Timing per step
```

### End-to-End Flow

```
User Input (JSON)
    │
    ▼
[InputNormalizer] → ClinicalRecord
    │
    ▼
[ClinicalRuleEngine] → ClinicalLabel[]
    │
    ▼
[EmbeddingTextBuilder] → embedding_text string
    │
    ├──────────────────────────────────────┐
    ▼                                      ▼
[SemanticRetriever]              [KeywordRetriever]
[QdrantAdapter]                  [In-memory tokenizer]
    │                                      │
    ▼                                      ▼
RetrievalResult[]               RetrievalResult[]
    │                                      │
    └──────────────┬───────────────────────┘
                   ▼
          [SymbolicRetriever]
          [Label/Risk match]
                   │
                   ▼
          RetrievalResult[]
                   │
                   ▼
          [GraphRetriever]
          [Neo4jAdapter]
                   │
                   ▼
          RetrievalResult[]
                   │
                   ▼
          [ResultMerger]
                   │
                   ▼
          Ranked RetrievalResult[]
                   │
                   ▼
          [ExplanationGenerator]
                   │
                   ▼
          RetrievalBundle → JSON Output
```

---

## 6. Error Handling Strategy

| Error Type | Behavior |
|---|---|
| **ValidationError** (bad input) | Halt immediately. Return error to caller. |
| **ToolExecutionError** (tool failed) | Log error, skip tool, continue pipeline. |
| **ConnectionError** (DB down) | Log error, skip dependent tools, return partial results. |
| **TimeoutError** (tool too slow) | Log timeout, skip tool, continue. |

Design principle: **Graceful degradation** — one DB going down shouldn't crash the whole pipeline.

---

## 7. Tool Interface Contract

```python
from abc import ABC, abstractmethod

class BaseTool(ABC):
    """Every tool must implement this interface."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier (snake_case)."""
        ...

    @property
    @abstractmethod
    def dependencies(self) -> list[str]:
        """Tools that must run before this one."""
        ...

    @abstractmethod
    def run(self, ctx: OrchestrationContext) -> OrchestrationContext:
        """Execute this tool and return updated context."""
        ...
```

---

## 8. Auditing & Logging

Every tool call is logged with:

```json
{
  "tool": "ClinicalRuleEngine",
  "started_at": "2026-06-17T15:30:00.123Z",
  "duration_ms": 2.3,
  "input_summary": {"vital_count": 5, "record_id": "REC001"},
  "output_summary": {"labels_count": 3},
  "error": null
}
```

Each `RetrievalResult` includes provenance:
- Which retrieval path(s) found it
- Which clinical labels triggered the match
- Which evidence values were used

This makes the system **auditable for clinical use**.

---

## 9. Implementation Roadmap

### Phase 1 — Core Pipeline (Tools 1–9)
Build the fundamental RAG orchestration pipeline without database adapters.

| # | Tool | Depends On | Effort |
|---|---|---|---|
| 1 | InputNormalizer | — | Small |
| 2 | ClinicalRuleEngine | InputNormalizer | Small |
| 3 | EmbeddingTextBuilder | ClinicalRuleEngine | Small |
| 4 | SemanticRetriever | EmbeddingTextBuilder | Medium |
| 5 | KeywordRetriever | InputNormalizer | Medium |
| 6 | SymbolicRetriever | ClinicalRuleEngine | Small |
| 7 | GraphRetriever | ClinicalRuleEngine | Medium |
| 8 | ResultMerger | All retrievers | Medium |
| 9 | ExplanationGenerator | ResultMerger | Small |

### Phase 2 — Database Adapters (Tools 10–12)
Connect to the actual databases.

| # | Tool | Depends On | Effort |
|---|---|---|---|
| 10 | PostgresAdapter | — | Medium |
| 11 | QdrantAdapter | — | Medium |
| 12 | Neo4jAdapter | — | Medium |

### Phase 3 — Orchestrator + Integration
Wire everything together.

| Component | Depends On | Effort |
|---|---|---|
| Orchestrator class | All tools | Medium |
| CLI entry point | Orchestrator | Small |
| API endpoint (FastAPI) | Orchestrator | Small |
| Configuration system | — | Small |
| Integration tests | Everything | Medium |

---

## 10. File Structure (Proposed)

```
health_panel/
├── pulsepanel_orchestrator/        ← NEW
│   ├── __init__.py                  # Public API
│   ├── orchestrator.py              # Central orchestrator
│   ├── context.py                   # OrchestrationContext dataclass
│   ├── base.py                      # BaseTool abstract class
│   ├── errors.py                    # Typed exceptions
│   ├── logging.py                   # Audit logging
│   │
│   ├── tools/                       # ← Each tool in its own file
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
│   │
│   ├── config/                      # Configuration
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   └── rules.py                 # Clinical rule definitions
│   │
│   └── tests/                       # Tests for each tool
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
├── pulsepanel_rag/                  ← Existing (from feature branch)
│   ├── models.py                    # Reuse/extend these models
│   ├── clinical_rules.py
│   ├── embedding_text.py
│   ├── retrieval.py                 # HybridRetriever → migrate to tools
│   ├── mock_data.py
│   └── demo.py
│
├── docs/
│   ├── Pulsepanel_clinical_graphrag_architecture.md
│   ├── pulsepanel_orchestration_layer.md  ← THIS DOCUMENT
│   ├── pulsepanel_end_to_end_architecture.md
│   └── pulsepanel_integration_plan.md
│
├── scripts/
│   └── start-dbs.sh               # Database helper script
├── docker-compose.yml               # PostgreSQL, Qdrant, Neo4j
├── requirements.txt                 # Python dependencies
├── .gitignore                       # Git ignore rules
├── .env.example                     # Environment variable template
└── README.md
```

---

## 11. Key Design Decisions

| Decision | Rationale |
|---|---|
| **Tool-per-file** | One tool = one responsibility = easy to test |
| **Context object** | Avoids spaghetti function signatures; enables easy tracing |
| **Graceful degradation** | One DB failure shouldn't halt clinical triage |
| **Deterministic rules** | Clinical safety requires reproducible label derivation |
| **Weighted hybrid scoring** | Balances semantic understanding with exact clinical matching |
| **Step-by-step pipeline** | Each step is independently testable and auditable |

---

## 12. Summary

The orchestration layer is built as a **pure Python tool-based pipeline** where:

1. **Each tool is a standalone class** with one job
2. **The orchestrator coordinates** the tool execution sequence
3. **The context object carries data** between tools
4. **Every step is logged** for auditability
5. **Errors are handled gracefully** — partial results are better than no results
6. **Scoring is transparent** — you can trace why any document was ranked where
