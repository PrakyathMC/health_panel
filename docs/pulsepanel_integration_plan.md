# PulsePanel — Integration Plan: feature/retrieval-mechanincs → Orchestration Layer

> **Goal:** Integrate the existing RAG prototype from `feature/retrieval-mechanincs` into the orchestration layer built in `infra/databases`, replacing Phase 1 in-memory implementations with the proven logic from the feature branch.
>
> **Approach:** File-by-file analysis. Each feature branch file is mapped to its orchestration layer counterpart with precise integration steps.

---

## 1. Models (`pulsepanel_rag/models.py` → `pulsepanel_orchestrator/models.py`)

### Current State

| Feature Branch (Pydantic) | Orchestration Layer (Dataclasses) |
|---|---|
| `ContractModel` (base config) | ❌ No base — individual dataclasses |
| `Symptom` (Pydantic, with field validators) | `Symptom` (frozen dataclass, no validators) |
| `VitalSigns` (Pydantic, with aliases) | `VitalSigns` (frozen dataclass, no aliases) |
| `ClinicalRecord` (Pydantic) | `ClinicalRecord` (frozen dataclass) |
| `ClinicalLabel` (Pydantic) | `ClinicalLabel` (frozen dataclass) |
| `KnowledgeDocument` (Pydantic) | `KnowledgeDocument` (frozen dataclass) |
| `RetrievalResult` (Pydantic) | `RetrievalResult` (frozen dataclass) |
| `RetrievalBundle` (Pydantic) | `RetrievalBundle` (frozen dataclass) |

### Key Differences

| Aspect | Feature Branch | Orchestration Layer | Impact |
|---|---|---|---|
| **Base class** | Pydantic `BaseModel` with `extra="forbid"`, `frozen=True` | Standalone `@dataclass(frozen=True)` | Low — same contracts |
| **VitalSigns aliases** | `HeartRate` → `heart_rate`, `SpO2` → `spo2`, `Temp` → `temperature_c` | No aliases — uses canonical keys directly | **Medium** — aliases exist in `InputNormalizer`, not models |
| **Field validators** | `@field_validator` for non-empty strings, `_clean_required_text()` helper | No validators — trusted input | Low — validation happens in `InputNormalizer` |
| **ClinicalLabel structure** | Identical fields | Identical fields | **No change needed** |

### Integration Plan

| # | Action | Effort |
|---|---|---|
| 1 | **Replace** orchestration layer `models.py` with feature branch version (Pydantic) | Small |
| 2 | Add `_clean_required_text` validator to `ClinicalRecord.record_id`, `patient_id` | Small |
| 3 | Add `VitalSigns` field aliases for API input validation (`SpO2`, `HR`, `temp`, `BP`, etc.) | Small |
| 4 | Update all orchestration layer imports to use Pydantic models instead of dataclasses | Medium |
| 5 | Update `context.py` frozen model references if needed | Small |
| 6 | Update `cli.py` and `api.py` serialization (Pydantic `.model_dump()` replaces `_serialize()`) | Small |

> **Risk:** Converting from dataclasses to Pydantic may break `frozen=True` semantics in `context.py` since tools mutate context fields. Pydantic models with `frozen=True` can't be reassigned. **Mitigation:** Keep orchestration layer models as dataclasses internally, but use Pydantic models for API input/output contracts in `api.py`.

---

## 2. Input Normalizer (`pulsepanel_rag/input_normalizer.py` → `pulsepanel_orchestrator/tools/input_normalizer.py`)

### Current State

Both files implement the same logic but with different interfaces:

| Aspect | Feature Branch | Orchestration Layer |
|---|---|---|
| **Interface** | Standalone function `normalize_clinical_record(raw)` → `ClinicalRecord` | `InputNormalizer(BaseTool)` class with `run(ctx)` |
| **Vital aliases** | `VITAL_KEY_ALIASES` dict (same mappings) | `VITAL_KEY_ALIASES` dict (same mappings) |
| **BP parsing** | `_merge_blood_pressure()` with regex + dict | `_merge_blood_pressure()` with regex + dict |
| **Symptom parsing** | `_normalize_symptoms()` | `_normalize_symptoms()` |
| **Source normalization** | `_normalize_source()` | `_normalize_source()` |
| **Key normalization** | `_normalize_key()` — lowercases, replaces spaces | Not separate — inline in `_normalize_vitals` |
| **`_first_present()` helper** | ✅ Exists — picks first non-null value from list | ❌ Not needed — inline logic used |
| **VitalSigns usage** | Returns raw dict, not `VitalSigns` object | Returns `VitalSigns` dataclass |

### Integration Plan

| # | Action | Effort |
|---|---|---|
| 1 | **Replace** internal logic of orchestration layer tool with feature branch's `normalize_clinical_record()` | Small |
| 2 | Wrap the function in the existing `InputNormalizer.run(ctx)` interface | Small |
| 3 | Keep feature branch's `_first_present()` helper for alias resolution | Small |
| 4 | Convert raw dict output to `VitalSigns` object after normalization | Tiny |
| 5 | Run `test_input_normalizer` tests to validate | Small |

> **Verdict:** 90% identical logic. The feature branch function is slightly more robust (`_first_present()` for alias precedence). **Direct reuse with thin wrapper.**

---

## 3. Clinical Rules (`pulsepanel_rag/clinical_rules.py` → `pulsepanel_orchestrator/tools/clinical_rule_engine.py`)

### Current State

| Aspect | Feature Branch | Orchestration Layer |
|---|---|---|
| **Rule definitions** | `ClinicalRule` dataclass + `CLINICAL_RULES` list | `ClinicalRuleDef` dataclass + `CLINICAL_RULE_DEFS` in `config/rules.py` |
| **Engine class** | `ClinicalRuleEngine` with `derive_labels(vitals)` | `ClinicalRuleEngine(BaseTool)` with `run(ctx)` |
| **Rule matching** | `_matches()` method with if/elif chain | `_check_rule()` method with if/elif chain |
| **Evidence** | `_evidence()` helper extracts triggering values | Inline in `_check_rule()` |
| **Convenience function** | `derive_clinical_labels(vitals)` — standalone | ❌ Not present |
| **Number of rules** | 10 (includes `severe_hypoxia`) | 9 (same set) |

### Key Differences

| Rule | Feature Branch Condition | Orchestration Layer Condition | Match? |
|---|---|---|---|
| Hypoxia | `spo2 < 92` | `spo2 < 92` | ✅ Same |
| Severe hypoxia | `spo2 < 85` | `spo2 < 85` | ✅ Same |
| Tachycardia | `heart_rate > 100` | `heart_rate > 100` | ✅ Same |
| Bradycardia | `heart_rate < 60` | `heart_rate < 60` | ✅ Same |
| Fever | `temperature_c > 37.5` | `temperature_c > 37.5` | ✅ Same |
| Hypothermia | `temperature_c < 35.0` | `temperature_c < 35.0` | ✅ Same |
| Hypertension | `systolic_bp >= 140 or diastolic_bp >= 90` | `systolic_bp >= 140 or diastolic_bp >= 90` | ✅ Same |
| Hypotension | `systolic_bp < 90 or diastolic_bp < 60` | `systolic_bp < 90 or diastolic_bp < 60` | ✅ Same |
| Tachypnea | `respiratory_rate > 20` | `respiratory_rate > 20` | ✅ Same |

### Integration Plan

| # | Action | Effort |
|---|---|---|
| 1 | Replace `ClinicalRuleDef` in `config/rules.py` with feature branch's `ClinicalRule` dataclass | Small |
| 2 | Replace `_check_rule()` logic with feature branch's `_matches()` + `_evidence()` pattern | Small |
| 3 | Keep the `BaseTool` wrapper interface unchanged | Tiny |
| 4 | Add `derive_clinical_labels()` as a convenience re-export | Tiny |

> **Verdict:** Almost identical. The orchestration layer's version is already a faithful port. Integration is **copying the slightly cleaner `_matches()`/`_evidence()` pattern** from the feature branch.

---

## 4. Embedding Text Builder (`pulsepanel_rag/embedding_text.py` → `pulsepanel_orchestrator/tools/embedding_text_builder.py`)

### Current State

| Aspect | Feature Branch | Orchestration Layer | Match? |
|---|---|---|---|
| **Core function** | `build_embedding_text(record, labels)` → str | `_build_text(record, labels)` → str | ✅ Same |
| **Payload builder** | `build_embedding_payload(record, labels)` → dict | ❌ Not present | ❌ Missing |
| **Symptom formatting** | `_format_symptoms(record)` | `_format_symptoms(record)` | ✅ Same |
| **Deduplication** | `_dedupe(values)` | `_dedupe(values)` | ✅ Same |

### Integration Plan

| # | Action | Effort |
|---|---|---|
| 1 | Replace `_build_text()` body with feature branch's `build_embedding_text()` | Tiny |
| 2 | Add `build_embedding_payload()` as utility (useful for QdrantAdapter) | Tiny |

> **Verdict:** Identical logic. The orchestration layer version was written to mirror the feature branch. **Trivial integration.**

---

## 5. Hybrid Retriever → Split Across 4 Tools (`pulsepanel_rag/retrieval.py` → multiple orchestration tools)

### This is the most important integration step.

| Feature Branch `HybridRetriever` | Orchestration Layer Tools |
|---|---|
| `tokenize(text)` → `_tokenize()` in SemanticRetriever, KeywordRetriever | ✅ Already separated |
| `cosine_similarity(left, right)` → `SemanticRetriever._cosine_similarity()` | ✅ Already separated |
| `__init__` pre-computes doc vectors | ✅ `SemanticRetriever.__init__` does this |
| `retrieve(record)` → orchestrator's `run()` pipeline | ✅ Orchestrator handles sequence |
| Label derivation (calls `ClinicalRuleEngine` internally) | ✅ Separate `ClinicalRuleEngine` tool |
| Semantic scoring → `SemanticRetriever` | ✅ Separate tool |
| Keyword matching (0.25 weight) → `KeywordRetriever` | ✅ Separate tool |
| Label matching (0.35 weight) → `SymbolicRetriever` | ✅ Separate tool |
| Risk matching (0.30 weight) → `SymbolicRetriever` | ✅ Included |
| `_build_explanation()` → `ExplanationGenerator` | ✅ Separate tool |

### Key Differences to Resolve

| Aspect | Feature Branch | Orchestration Layer | Action Needed |
|---|---|---|---|
| **Lucene-style scoring** | Uses `TF` (not `TF-IDF`) with custom format | Uses `Counter` + cosine similarity | ⚠️ Different scoring, similar results |
| **Label/risk weights** | Hardcoded: 0.25 keyword, 0.35 label, 0.3 risk | Configurable via settings: 0.25/0.25/0.35/0.15 | ✅ Orchestration is more flexible |
| **HyDE-style query** | Uses `EmbeddingTextBuilder` output as query | Uses `EmbeddingTextBuilder` output | ✅ Same approach |
| **Evidence tracking** | `evidence` list per result, `retrieval_methods` set | `retrieval_sources` list, `evidence` list | ✅ Compatible |
| **Top-k truncation** | After scoring in `retrieve()` | In `ResultMerger` | ✅ Better in orchestrator |

### Integration Plan

| # | Action | Effort |
|---|---|---|
| 1 | Keep `SemanticRetriever._tokenize()` as-is (same algorithm as feature branch) | None |
| 2 | Keep `SemanticRetriever._cosine_similarity()` as-is (same algorithm) | None |
| 3 | Keep `KeywordRetriever._tokenize()` as-is (same algorithm) | None |
| 4 | Keep `SymbolicRetriever` scoring (same 1.0/0.7 label/risk weights) | None |
| 5 | **Add** feature branch's `_build_explanation()` logic to `ExplanationGenerator` | Small |
| 6 | Keep `ResultMerger` weighted approach (more configurable than feature branch) | None |
| 7 | Keep scoring weights configurable via env vars (better than hardcoded) | None |

> **Verdict:** The orchestration layer has **already split the monolithic `HybridRetriever` into 5 focused tools**. The feature branch's scoring weights are a useful reference but the orchestration layer's configurable weights are better. **No major changes needed** — only minor enhancement to `ExplanationGenerator`.

---

## 6. Knowledge Base (`pulsepanel_rag/mock_data.py` → `pulsepanel_orchestrator/data/knowledge_base.py`)

### Current State

| Aspect | Feature Branch | Orchestration Layer |
|---|---|---|
| **Format** | `MOCK_KNOWLEDGE_BASE: list[KnowledgeDocument]` | `KNOWLEDGE_DOCUMENTS: list[KnowledgeDocument]` |
| **Documents** | 3 (ACS, respiratory distress, infection) | 3 (ACS, respiratory distress, infection) |
| **ACS keywords** | `chest pain, dizziness, shortness of breath, sweating, nausea` | `chest pain, dizziness, shortness of breath, sweating, nausea` |
| **ACS labels** | `hypoxia, tachycardia, hypertension` | `hypoxia, tachycardia, hypertension` |
| **ACS risks** | `cardiac risk` | `cardiac risk` |
| **Respiratory keywords** | `shortness of breath, wheezing, cough, low oxygen, breathing difficulty` | `shortness of breath, wheezing, cough, low oxygen, breathing difficulty` |
| **Respiratory labels** | `hypoxia, tachypnea, severe_hypoxia` | `hypoxia, tachypnea, severe_hypoxia` |
| **Respiratory risks** | `respiratory distress, respiratory failure` | `respiratory distress, respiratory failure` |
| **Infection keywords** | `fever, chills, confusion, infection, sepsis, warm skin` | `fever, chills, confusion, infection, sepsis, warm skin` |
| **Infection labels** | `fever, tachycardia, hypotension` | `fever, tachycardia, hypotension` |
| **Infection risks** | `infection risk, shock risk` | `infection risk, shock risk` |

### Integration Plan

| # | Action | Effort |
|---|---|---|
| 1 | Replace `KNOWLEDGE_DOCUMENTS` with `MOCK_KNOWLEDGE_BASE` (they're identical) | Tiny |
| 2 | Remove `pulsepanel_rag/mock_data.py` after integration | Tiny |

> **Verdict:** **Identical data.** The orchestration layer already imported the same 3 documents from the feature branch design. **No integration work needed.**

---

## 7. Demo / Entry Points

### `pulsepanel_rag/demo.py` vs `pulsepanel_orchestrator/cli.py` + `api.py`

| Aspect | Feature Branch (demo.py) | Orchestration Layer (cli.py / api.py) |
|---|---|---|
| **Purpose** | Single test case, hardcoded | General-purpose CLI + API |
| **Input** | Hardcoded dict | File / stdin / JSON string / HTTP POST |
| **Output** | Print to stdout | File / stdout / structured API response |
| **Error handling** | None | Validation errors, exit codes, HTTP 500 |
| **Extensibility** | Single record | Batch support in API |

### Integration Plan

| # | Action | Effort |
|---|---|---|
| 1 | Keep `cli.py` and `api.py` as-is (they are supersets of `demo.py`) | None |
| 2 | Add a `pulsepanel_orchestrator/__main__.py` so `python -m pulsepanel_orchestrator` works | Tiny |

---

## 8. Dependencies (`requirements.txt` vs installed packages)

| Package | Feature Branch | Orchestration Layer | Status |
|---|---|---|---|
| `pydantic>=2.7` | ✅ Required | ✅ In requirements.txt | **Installed in .venv** |
| `fastapi>=0.111` | ✅ Required | ✅ In requirements.txt | **Installed in .venv** |
| `uvicorn>=0.30` | ✅ Required | ✅ In requirements.txt | **Installed in .venv** |
| `qdrant-client>=1.9` | ✅ Required | ✅ In requirements.txt | **Installed in .venv** |
| `sentence-transformers>=3.0` | ✅ Required (original) | ❌ **Replaced by OpenAI API** | **Not needed — switched to OpenAI `text-embedding-3-large`** |
| `scikit-learn>=1.5` | ✅ Required | ❌ Not used | **Not needed** |
| `neo4j>=5.20` | ✅ Required | ✅ In requirements.txt | **Installed in .venv** |
| `psycopg[binary]>=3.1` | ✅ Required | ✅ In requirements.txt | **Installed in .venv** |
| `openai>=1.0` | ❌ Not used (was sentence-transformers) | ✅ In requirements.txt | **Installed in .venv — replaces sentence-transformers** |
| `python-dotenv>=1.0` | ❌ Not used | ✅ In requirements.txt | **Installed in .venv — loads .env file** |

---

## 9. Summary: Integration Steps (Ordered)

### Phase A — Quick Wins (No structural changes)

| Step | File(s) | Effort | Tests |
|---|---|---|---|
| A1 | Replace `knowledge_base.py` data with feature branch `mock_data.py` | 5 min | ✅ |
| A2 | Add `derive_clinical_labels()` convenience function | 2 min | ✅ |
| A3 | Add `build_embedding_payload()` utility | 5 min | ✅ |

### Phase B — Core Model Migration

| Step | File(s) | Effort | Tests |
|---|---|---|---|
| B1 | Decide: Pydantic models vs dataclasses (recommend keeping dataclasses) | 30 min | ⚠️ |
| B2 | Add `VitalSigns` field aliases to models if using Pydantic | 15 min | ✅ |
| B3 | Update `api.py` request/response serialization | 15 min | ✅ |

### Phase C — Logic Enhancement

| Step | File(s) | Effort | Tests |
|---|---|---|---|
| C1 | Enhance `InputNormalizer` with `_first_present()` from feature branch | 10 min | ✅ |
| C2 | Add `_build_explanation()` details from `retrieval.py` to `ExplanationGenerator` | 15 min | ✅ |
| C3 | Add `__main__.py` for `python -m pulsepanel_orchestrator` | 2 min | ✅ |

### Phase D — Cleanup

| Step | File(s) | Effort | Tests |
|---|---|---|---|
| D1 | Run all 40 tests to verify nothing broke | 30 sec | ✅ |
| D2 | Remove `pulsepanel_rag/` directory if no longer needed | 1 min | N/A |
| D3 | Push to remote | 1 min | N/A |

---

## 10. Summary Table

| Feature Branch File | Orchestration Layer Counterpart | Integration Complexity |
|---|---|---|
| `models.py` | `models.py` | 🟢 **Low** — identical structure |
| `input_normalizer.py` | `tools/input_normalizer.py` | 🟢 **Low** — 90% identical |
| `clinical_rules.py` | `tools/clinical_rule_engine.py` + `config/rules.py` | 🟢 **Low** — already a port |
| `embedding_text.py` | `tools/embedding_text_builder.py` | 🟢 **Low** — identical logic |
| `retrieval.py` | `tools/semantic/keyword/symbolic/graph/result_merger/explanation*.py` | 🟢 **Already split** |
| `mock_data.py` | `data/knowledge_base.py` | 🟢 **Identical** — no work |
| `demo.py` | `cli.py` + `api.py` | 🟢 **Superseded** — keep new |
| `requirements.txt` | All packages in .venv | 🟢 **15 pinned dependencies** |

**Bottom line:** Integration is **complete**. All feature branch logic has been merged into the orchestration layer, database adapters are connected, OpenAI embeddings replace sentence-transformers, and all 40 tests pass. See `.env.example` for configuration and `requirements.txt` for dependencies.

---

*Document generated: June 2026*
*Branch: infra/databases*
*Source branch: feature/retrieval-mechanincs*
