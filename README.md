# PulsePanel — Clinical GraphRAG Platform

A clinical data platform combining **PostgreSQL**, **Qdrant**, and **Neo4j** for structured, vector, and graph-based healthcare data storage.

Based on the [PulsePanel Clinical Data Architecture](docs/Pulsepanel_clinical_graphrag_architecture.md).

---

## 🏗️ Architecture (Option B)

| Database | Purpose | Port(s) | Dashboard |
|---|---|---|---|
| **PostgreSQL** | Structured clinical data store | `5432` | — |
| **Qdrant** | Vector database for semantic search | `6333` (REST), `6334` (gRPC) | http://localhost:6333/dashboard |
| **Neo4j** | Graph database for clinical relationships | `7474` (HTTP), `7687` (Bolt) | http://localhost:7474 |

---

## 🚀 Quick Start

> **Note:** Docker requires `sudo` on this system. All commands below use `sudo`.
> **Prerequisite:** Ensure **Docker Desktop WSL 2 integration** is enabled:
> 1. Open Docker Desktop → Settings → Resources → WSL Integration
> 2. Enable integration with your WSL distro
> 3. Apply & Restart

### Option 1 — Using the helper script (recommended)

```bash
# Copy env configuration
cp .env.example .env

# Start all databases
sudo ./scripts/start-dbs.sh up

# Check status of all databases
sudo ./scripts/start-dbs.sh status

# View logs
sudo ./scripts/start-dbs.sh logs

# Stop all databases
sudo ./scripts/start-dbs.sh down

# Restart all databases
sudo ./scripts/start-dbs.sh restart
```

### Option 2 — Using docker compose directly

```bash
# Copy env configuration
cp .env.example .env

# Start all databases
sudo docker compose --env-file .env up -d

# Check running containers
sudo docker compose ps

# View logs
sudo docker compose logs -f

# Stop all databases
sudo docker compose down
```

---

## 🔐 Default Credentials

| Service | Username | Password |
|---|---|---|
| PostgreSQL | `pulsepanel` | `pulsepanel_secret` |
| Neo4j | `neo4j` | `pulsepanel_graph` |
| Qdrant | — (no auth by default) | — |

> Change these in the `.env` file before deploying to any non-local environment.

---

## 📊 PostgreSQL Schema

The `docker/postgres/init.sql` file creates the following tables matching the architecture document:

- `patients` — Patient records
- `visits` — Visit/encounter records
- `symptoms` — Patient & doctor-reported symptoms
- `vitals` — Raw numerical vitals (SpO₂, HR, BP, Temp, etc.)
- `lab_reports` — Objective lab/diagnostic values
- `clinical_labels` — Derived labels from clinical rules (hypoxia, tachycardia, etc.)
- `clinical_facts` — Human-readable clinical statements
- `risk_concepts` — Higher-level risk assessments
- `fhir_records` — Raw FHIR/EHR resources
- `canonical_records` — Normalized clinical records (Section 8 format)
- `audit_log` — Audit trail for all changes
- `clinical_rules` — Registry of deterministic label-generation rules

Pre-seeded with 7 clinical rules (hypoxia, tachycardia, fever, hypertension, etc.).

---

## 🐍 Python Setup (Orchestration Layer)

The PulsePanel orchestrator runs on Python 3.12+. Use the virtual environment:

```bash
# Activate the virtual environment
source .venv/bin/activate

# Install dependencies (if setting up from scratch)
pip install -r requirements.txt

# Run the analysis via CLI
python -m pulsepanel_orchestrator.cli --json '{"record_id":"test","patient_id":"P001","query":"Chest pain","symptoms":["Chest pain"],"vitals":{"SpO2":90,"HR":110}}'

# Or start the API server
uvicorn pulsepanel_orchestrator.api:app --host 127.0.0.1 --port 8989

# Run tests
pytest pulsepanel_orchestrator/tests/ -v
```

> **Note:** The `.env` file is automatically loaded by `python-dotenv`. Copy `.env.example` to `.env` and add your `OPENAI_API_KEY` before using the Qdrant vector store.

---

## 🧪 Verifying the Database Setup

```bash
# Check all containers are running
sudo docker compose ps

# Check PostgreSQL
sudo docker compose exec postgres psql -U pulsepanel -d pulsepanel -c "\dt"

# Check Qdrant health
curl -s http://localhost:6333/healthz

# Check Neo4j
sudo docker compose exec neo4j cypher-shell -u neo4j -p pulsepanel_graph "MATCH (n) RETURN count(n) AS node_count"
```

---

## 📁 Project Structure

```
health_panel/
├── docker/
│   └── postgres/
│       └── init.sql          # PostgreSQL schema + seed data
├── pulsepanel_orchestrator/      # Python orchestration layer
│   ├── orchestrator.py            # Central pipeline coordinator
│   ├── api.py                     # FastAPI server
│   ├── cli.py                     # CLI entry point
│   ├── tools/                     # RAG pipeline tools
│   ├── config/                    # Settings & rules
│   └── tests/                     # 40+ tests
├── docs/
│   ├── Pulsepanel_clinical_graphrag_architecture.md
│   ├── pulsepanel_orchestration_layer.md
│   ├── pulsepanel_end_to_end_architecture.md
│   └── pulsepanel_integration_plan.md
├── scripts/
│   └── start-dbs.sh               # Helper script (handles sudo)
├── docker-compose.yml             # All 3 database services
├── requirements.txt               # Python dependencies
├── .gitignore                     # Git ignore rules
├── .env.example                   # Environment variable template
└── README.md
```
