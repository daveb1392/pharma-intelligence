#!/usr/bin/env bash
#
# Health check: verify scrapers ran recently and produced data.
# Exit 0 = healthy, exit 1 = problem detected.
#
# Usage:
#   ./deploy/healthcheck.sh              # check all
#   ./deploy/healthcheck.sh --verbose    # show details
#
set -euo pipefail

VERBOSE="${1:-}"
PROJECT_DIR="/opt/pharma-intelligence"
LOG_DIR="/var/log/pharma"
WARN=0

warn() {
    echo "WARNING: $*"
    WARN=1
}

info() {
    [[ "$VERBOSE" == "--verbose" ]] && echo "  $*"
    return 0
}

echo "=== Pharma Intelligence Health Check ==="
echo "Time: $(date)"

# 1. Check systemd timers are active
for timer in pharma-full-scrape.timer pharma-daily-tracker.timer; do
    if systemctl is-active --quiet "$timer" 2>/dev/null; then
        info "OK: $timer is active"
    else
        warn "$timer is not active"
    fi
done

# 2. Check log files exist and were written recently (within 36 hours)
for log in full_scrape.log daily_tracker.log; do
    logfile="${LOG_DIR}/${log}"
    if [[ ! -f "$logfile" ]]; then
        warn "Log file missing: $logfile"
        continue
    fi
    age_seconds=$(( $(date +%s) - $(stat -c %Y "$logfile" 2>/dev/null || stat -f %m "$logfile" 2>/dev/null) ))
    age_hours=$(( age_seconds / 3600 ))
    if (( age_hours > 36 )); then
        warn "$log not updated in ${age_hours}h (>36h)"
    else
        info "OK: $log updated ${age_hours}h ago"
    fi
done

# 3. Check disk space (warn if < 2GB free)
avail_kb=$(df --output=avail /opt 2>/dev/null | tail -1 || df -k /opt | tail -1 | awk '{print $4}')
avail_gb=$(( avail_kb / 1048576 ))
if (( avail_gb < 2 )); then
    warn "Low disk space: ${avail_gb}GB free"
else
    info "OK: ${avail_gb}GB free"
fi

# 4. Check Python venv exists
if [[ -f "${PROJECT_DIR}/venv/bin/python" ]]; then
    info "OK: Python venv exists"
else
    warn "Python venv missing at ${PROJECT_DIR}/venv/"
fi

# 5. Check .env exists
if [[ -f "${PROJECT_DIR}/.env" ]]; then
    info "OK: .env file exists"
else
    warn ".env file missing"
fi

echo ""
if (( WARN > 0 )); then
    echo "UNHEALTHY — issues detected above"
    exit 1
else
    echo "HEALTHY"
    exit 0
fi
