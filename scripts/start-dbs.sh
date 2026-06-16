#!/bin/bash
# ============================================================
# PulsePanel - Database Startup Script
# ============================================================
# Run with: sudo ./scripts/start-dbs.sh
# Or:       bash scripts/start-dbs.sh (will prompt for sudo)
# ============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"
ENV_FILE="$PROJECT_DIR/.env"

# Detect if we need sudo
if [ "$EUID" -ne 0 ]; then
    echo "[INFO] Docker requires root privileges. Re-running with sudo..."
    exec sudo bash "$0" "$@"
fi

# Check if .env exists, if not copy from .env.example
if [ ! -f "$ENV_FILE" ]; then
    echo "[INFO] No .env file found. Creating from .env.example..."
    cp "$ENV_FILE.example" "$ENV_FILE"
    echo "[INFO] Created $ENV_FILE — edit it to customize passwords."
fi

cd "$PROJECT_DIR"

case "${1:-up}" in
    up)
        echo "=========================================="
        echo "  PulsePanel — Starting Databases"
        echo "=========================================="
        echo "  PostgreSQL → localhost:5432"
        echo "  Qdrant     → localhost:6333"
        echo "  Neo4j      → localhost:7474 (UI) / 7687 (Bolt)"
        echo "=========================================="
        docker compose --env-file "$ENV_FILE" up -d
        echo ""
        echo "[✓] Databases started. Check status with: docker compose ps"
        ;;
    down)
        echo "=========================================="
        echo "  PulsePanel — Stopping Databases"
        echo "=========================================="
        docker compose --env-file "$ENV_FILE" down
        echo "[✓] Databases stopped."
        ;;
    restart)
        echo "=========================================="
        echo "  PulsePanel — Restarting Databases"
        echo "=========================================="
        docker compose --env-file "$ENV_FILE" restart
        echo "[✓] Databases restarted."
        ;;
    logs)
        docker compose --env-file "$ENV_FILE" logs -f "${2:-}"
        ;;
    ps)
        docker compose --env-file "$ENV_FILE" ps
        ;;
    status)
        echo "=== PostgreSQL ==="
        docker compose --env-file "$ENV_FILE" exec postgres pg_isready -U pulsepanel 2>/dev/null || echo "  Not connected"
        echo ""
        echo "=== Qdrant ==="
        curl -sf http://localhost:6333/healthz 2>/dev/null && echo "  Connected ✓" || echo "  Not connected"
        echo ""
        echo "=== Neo4j ==="
        local neo4j_pass
neo4j_pass="$(grep NEO4J_PASSWORD "$ENV_FILE" 2>/dev/null | cut -d= -f2)"
neo4j_pass="${neo4j_pass:-pulsepanel_graph}"
docker compose --env-file "$ENV_FILE" exec neo4j cypher-shell -u neo4j -p "$neo4j_pass" "RETURN 1 AS health" 2>/dev/null || echo "  Not connected"
        ;;
    *)
        echo "Usage: $0 {up|down|restart|logs|ps|status}"
        echo ""
        echo "  up        — Start all databases (default)"
        echo "  down      — Stop all databases"
        echo "  restart   — Restart all databases"
        echo "  logs      — View logs (add service name to filter)"
        echo "  ps        — List running containers"
        echo "  status    — Check health of all databases"
        exit 1
        ;;
esac
