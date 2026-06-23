# PulsePanel Clinical GraphRAG Platform

A clinical data platform combining PostgreSQL, Qdrant, and Neo4j for structured,
vector, and graph-based healthcare data storage.

Based on the [PulsePanel Clinical Data Architecture](docs/Pulsepanel_clinical_graphrag_architecture.md).

## Architecture

| Database | Purpose | Port(s) | Dashboard |
|---|---|---|---|
| PostgreSQL | Structured clinical data store | `5432` | - |
| Qdrant | Vector database for semantic search | `6333` REST, `6334` gRPC | http://localhost:6333/dashboard |
| Neo4j | Graph database for clinical relationships | `7474` HTTP, `7687` Bolt | http://localhost:7474 |

## Quick Start

Copy env configuration:

```bash
cp .env.example .env
```

Start all databases:

```bash
sudo ./scripts/start-dbs.sh up
```

Check status:

```bash
sudo ./scripts/start-dbs.sh status
```

Stop all databases:

```bash
sudo ./scripts/start-dbs.sh down
```

Or use Docker Compose directly:

```bash
sudo docker compose --env-file .env up -d
sudo docker compose ps
sudo docker compose logs -f
sudo docker compose down
```

## Default Credentials

| Service | Username | Password |
|---|---|---|
| PostgreSQL | `pulsepanel` | `pulsepanel_secret` |
| Neo4j | `neo4j` | `pulsepanel_graph` |
| Qdrant | - | - |

Change these in `.env` before deploying anywhere outside local development.

## Python Setup

The PulsePanel orchestrator runs on Python 3.12+.

```bash
pip install -r requirements.txt
```

Run the orchestrator CLI:

```bash
python -m pulsepanel_orchestrator.cli --json '{"record_id":"test","patient_id":"P001","query":"Chest pain","symptoms":["Chest pain"],"vitals":{"SpO2":90,"HR":110}}'
```

Start the API server:

```bash
uvicorn pulsepanel_orchestrator.api:app --host 127.0.0.1 --port 8989
```

Run orchestrator tests:

```bash
pytest pulsepanel_orchestrator/tests/ -v
```

Seed Qdrant with clinical knowledge embeddings:

```bash
python scripts/seed_qdrant.py --smoke-query "chest pain and low oxygen"
```

Run the standalone RAG prototype:

```bash
python -m pulsepanel_rag.demo
python -m unittest discover -s tests
```

The `.env` file is ignored by Git. Copy `.env.example` to `.env` and add
`OPENAI_API_KEY` locally before using OpenAI embeddings or Qdrant vector search.

## Database Verification

```bash
sudo docker compose ps
sudo docker compose exec postgres psql -U pulsepanel -d pulsepanel -c "\dt"
curl -s http://localhost:6333/healthz
sudo docker compose exec neo4j cypher-shell -u neo4j -p pulsepanel_graph "MATCH (n) RETURN count(n) AS node_count"
```

## Project Structure

```text
health_panel/
├── docker/postgres/init.sql
├── pulsepanel_orchestrator/
│   ├── orchestrator.py
│   ├── api.py
│   ├── cli.py
│   ├── tools/
│   ├── config/
│   └── tests/
├── pulsepanel_rag/
│   ├── models.py
│   ├── input_normalizer.py
│   ├── clinical_rules.py
│   ├── embedding_text.py
│   └── retrieval.py
├── docs/
├── scripts/start-dbs.sh
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```
