#!/usr/bin/env bash
#
# Run all pharmacy scrapers (Phase 1 + Phase 2) sequentially.
# Designed for Hetzner scraper server or local dev.
#
# Usage:
#   ./scripts/run_full_scrape.sh           # all pharmacies
#   ./scripts/run_full_scrape.sh punto_farma  # single pharmacy
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

LOG_DIR="${PROJECT_DIR}/logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/full_scrape_${TIMESTAMP}.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

run_scraper() {
    local name="$1"
    shift
    log "START: $name"
    if python "$@" 2>&1 | tee -a "$LOG_FILE"; then
        log "DONE:  $name"
    else
        log "FAIL:  $name (exit $?)"
    fi
}

FILTER="${1:-all}"

log "=========================================="
log "FULL SCRAPE - filter=${FILTER}"
log "=========================================="

if [[ "$FILTER" == "all" || "$FILTER" == "farma_oliva" ]]; then
    run_scraper "Farma Oliva" -m scrapers.farma_oliva
fi

if [[ "$FILTER" == "all" || "$FILTER" == "punto_farma" ]]; then
    run_scraper "Punto Farma Phase 1" -m scrapers.punto_farma phase1
    run_scraper "Punto Farma Phase 2" -m scrapers.punto_farma phase2
fi

if [[ "$FILTER" == "all" || "$FILTER" == "farma_center" ]]; then
    run_scraper "Farma Center Phase 1" -m scrapers.farmacia_center phase1
    run_scraper "Farma Center Phase 2" -m scrapers.farmacia_center phase2
fi

if [[ "$FILTER" == "all" || "$FILTER" == "farmacia_catedral" ]]; then
    run_scraper "Farmacia Catedral Phase 1" -m scrapers.farmacia_catedral phase1
    run_scraper "Farmacia Catedral Phase 2" -m scrapers.farmacia_catedral phase2
fi

log "=========================================="
log "FULL SCRAPE COMPLETE"
log "=========================================="
