#!/data/data/com.termux/files/usr/bin/bash
# fsserver-lib.sh — shared helpers for Family Safety server control
# v2.0 — with preflight, timing, crash detection, watchdog

# ---- Colors ----
c_reset=$'\033[0m'
c_bold=$'\033[1m'
c_dim=$'\033[2m'
c_red=$'\033[31m'
c_grn=$'\033[32m'
c_yel=$'\033[33m'
c_blu=$'\033[34m'
c_mag=$'\033[35m'
c_cyn=$'\033[36m'

# ---- Paths ----
FS_HOME="$HOME/FamilySafety"
FS_SOCKET="$HOME/.tailscale/tailscaled.sock"
FS_STATE_DIR="$HOME/.fsserver"
FS_STATE_FILE="$FS_STATE_DIR/state.json"
FS_CRASH_MARKER="$FS_STATE_DIR/last-run-crashed"
FS_LOG_FILE="$FS_STATE_DIR/history.log"

mkdir -p "$FS_STATE_DIR"

# ---- Output helpers ----
hr()      { printf '%*s\n' 60 '' | tr ' ' '─'; }
title()   { echo "${c_bold}$*${c_reset}"; }
info()    { echo "  ${c_dim}$*${c_reset}"; }
ok()      { echo "  ${c_grn}✓${c_reset} $*"; }
bad()     { echo "  ${c_red}✗${c_reset} $*"; }
warn()    { echo "  ${c_yel}!${c_reset} $*"; }
step()    { echo "  ${c_blu}▸${c_reset} $*"; }
done_()   { echo "  ${c_mag}●${c_reset} $*"; }

# Log to history file
log_history() {
    local ts; ts=$(date -Iseconds)
    echo "[$ts] $*" >> "$FS_LOG_FILE"
}

# Run a command, time it, return duration in ms
# Usage: t0=$(now_ms); cmd; elapsed=$(( $(now_ms) - t0 ))
now_ms() {
    if date +%s%N >/dev/null 2>&1; then
        echo $(( $(date +%s%N) / 1000000 ))
    else
        echo $(( $(date +%s) * 1000 ))
    fi
}

# Check if a runit service is running
sv_running() {
    sv status "$1" 2>/dev/null | grep -q "^run:"
}

# Preflight check: verify required binaries exist
preflight() {
    local missing=()
    for bin in bash sv tailscale tailscale-cli curl python; do
        command -v "$bin" >/dev/null 2>&1 || missing+=("$bin")
    done
    if [ ${#missing[@]} -gt 0 ]; then
        bad "Missing required commands: ${missing[*]}"
        return 1
    fi
    [ -d "$FS_HOME" ] || { bad "FamilySafety dir not found: $FS_HOME"; return 1; }
    return 0
}

# Wait until backend responds to /health
# Usage: wait_backend <max_seconds>
wait_backend() {
    local max="${1:-30}" i=0
    while [ "$i" -lt "$max" ]; do
        if curl -s --max-time 2 http://127.0.0.1:8000/health 2>/dev/null | grep -q '"status":"ok"'; then
            return 0
        fi
        i=$((i+1))
        sleep 1
    done
    return 1
}

# Wait until tailscale socket exists
wait_socket() {
    local max="${1:-30}" i=0
    while [ "$i" -lt "$max" ]; do
        [ -S "$FS_SOCKET" ] && return 0
        i=$((i+1))
        sleep 1
    done
    return 1
}

# Wait until tailscale tunnel is up
wait_tunnel() {
    local max="${1:-30}" i=0
    while [ "$i" -lt "$max" ]; do
        if tailscale --socket="$FS_SOCKET" status 2>/dev/null | grep -q "100\."; then
            return 0
        fi
        i=$((i+1))
        sleep 1
    done
    return 1
}

# Get tailscale IPv4
get_ip() {
    [ -S "$FS_SOCKET" ] || { echo ""; return; }
    tailscale --socket="$FS_SOCKET" ip -4 2>/dev/null | head -1
}

# Save state JSON
save_state() {
    local status="$1"
    local ip; ip=$(get_ip)
    cat > "$FS_STATE_FILE" <<JSON
{
  "status": "$status",
  "ts": "$(date -Iseconds)",
  "tailscale_ip": "$ip",
  "backend_healthy": $(curl -s --max-time 2 http://127.0.0.1:8000/health 2>/dev/null | grep -q '"status":"ok"' && echo true || echo false),
  "fs_api": $([ "$(sv_running fs-api)" ] && echo true || echo false),
  "fs_serve": $([ "$(sv_running fs-serve)" ] && echo true || echo false),
  "tailscaled": $([ "$(sv_running tailscaled)" ] && echo true || echo false)
}
JSON
}

# Print summary footer
print_summary() {
    local ip; ip=$(get_ip)
    hr
    echo "  ${c_bold}Tailscale IP :${c_reset} ${c_cyn}${ip:-—}${c_reset}"
    echo "  ${c_bold}Local URL    :${c_reset} http://127.0.0.1:8000/"
    [ -n "$ip" ] && echo "  ${c_bold}Remote URL   :${c_reset} http://$ip:8000/"
    [ -n "$ip" ] && echo "  ${c_bold}HTTPS (ts)   :${c_reset} https://${ip//./-}.ts.net (tailnet only)"
    hr
}

# Crash detection: check if previous run didn't reach "stopped"
check_previous_crash() {
    if [ -f "$FS_CRASH_MARKER" ]; then
        local prev
        prev=$(cat "$FS_CRASH_MARKER" 2>/dev/null)
        warn "Previous run may have crashed or was killed (last marker: $prev)"
        warn "Run 'fsserver logs fs-api' to inspect"
        return 0
    fi
    return 1
}

mark_running() {
    echo "running" > "$FS_CRASH_MARKER"
}

mark_stopped() {
    rm -f "$FS_CRASH_MARKER"
}

# ============================================================
# VISIBLE LENGTH HELPERS (ignore ANSI escapes)
# ============================================================
strip_ansi() { sed 's/\x1b\[[0-9;]*m//g'; }

# Print colored cell padded to N visible chars
# Usage: cell_colored "text" "\033[32m" "OK" 12
cell_colored() {
    local pre="$1" colored="$2" plain="$3" width="$4"
    local pad=$(( width - ${#plain} ))
    [ $pad -lt 0 ] && pad=0
    printf '%s%s%s%*s' "$pre" "$colored" "$c_reset" "$pad" ""
}

# ============================================================
# TABLE RENDERING
# ============================================================
# Terminal width (default 62, use COLUMNS if set)
term_width() { echo "${COLUMNS:-62}"; }

# Print table header with box-drawing chars
# Usage: table_header "Column1" "Column2" ...
table_header() {
    local cols=("$@")
    local widths=()
    for c in "${cols[@]}"; do widths+=(${#c}); done
    
    printf '  ┌'
    for i in "${!cols[@]}"; do
        printf '─%.0s' $(seq 1 $((widths[i]+2)))
        [ $i -lt $((${#cols[@]}-1)) ] && printf '┬'
    done
    printf '┐\n'
    
    printf '  │'
    for i in "${!cols[@]}"; do
        printf ' %s ' "${cols[i]}"
    done
    printf '│\n'
    
    printf '  ├'
    for i in "${!cols[@]}"; do
        printf '─%.0s' $(seq 1 $((widths[i]+2)))
        [ $i -lt $((${#cols[@]}-1)) ] && printf '┼'
    done
    printf '┤\n'
}

# Print table row
# Usage: table_row "val1" "val2" ...
table_row() {
    printf '  │'
    for v in "$@"; do
        printf ' %s ' "$v"
    done
    printf '│\n'
}

# Print row with status color
# Usage: table_row_status "OK" "value1" "value2"
table_row_status() {
    local status="$1"; shift
    local color=""
    local symbol=""
    case "$status" in
        OK|HEALTHY|RUNNING|UP|PASS)   color="$c_grn"; symbol="✓" ;;
        WARN|DEGRADED|SLOW)            color="$c_yel"; symbol="!" ;;
        FAIL|DOWN|UNREACHABLE|ERROR)  color="$c_red"; symbol="✗" ;;
        STOPPED|IDLE)                 color="$c_dim"; symbol="○" ;;
        *)                            color="$c_dim"; symbol="?" ;;
    esac
    printf '  │ %s%s %-7s%s │' "$color" "$symbol" "$status" "$c_reset"
    for v in "$@"; do
        printf ' %-*s │' 0 "$v"
    done
    printf '\n'
}

table_footer() {
    local cols=("$@")
    printf '  └'
    for i in "${!cols[@]}"; do
        printf '─%.0s' $(seq 1 $(( ${#cols[i]} + 2 )))
        [ $i -lt $((${#cols[@]}-1)) ] && printf '┴'
    done
    printf '┘\n'
}

# Simple 2-column key-value table (auto-aligned)
# Usage: kv_table "Key" "Value" ["Key" "Value" ...]
kv_table() {
    local pairs=("$@")
    local maxk=0
    for ((i=0; i<${#pairs[@]}; i+=2)); do
        [ ${#pairs[i]} -gt $maxk ] && maxk=${#pairs[i]}
    done
    for ((i=0; i<${#pairs[@]}; i+=2)); do
        printf '  %-*s : %s\n' "$maxk" "${pairs[i]}" "${pairs[i+1]}"
    done
}

# ============================================================
# MONITORING HELPERS (lightweight, no daemons)
# ============================================================

# CPU load average (1 min)
get_load() {
    awk '{print $1}' /proc/loadavg 2>/dev/null || echo "0.00"
}

# Memory usage: used/total in MB
get_mem() {
    if [ -f /proc/meminfo ]; then
        local total used
        total=$(awk '/^MemTotal:/ {print int($2/1024)}' /proc/meminfo)
        local avail
        avail=$(awk '/^MemAvailable:/ {print int($2/1024)}' /proc/meminfo)
        used=$((total - avail))
        echo "$used/$total"
    else
        echo "?/?"
    fi
}

# Backend memory usage (resident KB)
get_backend_rss() {
    local pid
    pid=$(pgrep -f "uvicorn backend.api.main:app" | head -1)
    if [ -n "$pid" ] && [ -r "/proc/$pid/status" ]; then
        awk '/^VmRSS:/ {print int($2/1024)}' "/proc/$pid/status" 2>/dev/null
    else
        echo "0"
    fi
}

# tailscaled memory usage (resident KB) — pgrep -f matches full cmdline
get_tailscaled_rss() {
    local pid
    pid=$(pgrep -f "bin/tailscaled" | head -1)
    if [ -n "$pid" ] && [ -r "/proc/$pid/status" ]; then
        awk '/^VmRSS:/ {print int($2/1024)}' "/proc/$pid/status" 2>/dev/null
    else
        echo "0"
    fi
}

# Battery level (Android) — tries sysfs, then termux-api
get_battery() {
    # 1) sysfs (works on most devices)
    local paths=(
        /sys/class/power_supply/battery/capacity
        /sys/class/power_supply/Battery/capacity
        /sys/class/power_supply/bms/capacity
    )
    for f in "${paths[@]}"; do
        if [ -r "$f" ]; then
            cat "$f" 2>/dev/null && return
        fi
    done
    # 2) termux-api (if termux-api package is installed)
    if command -v termux-battery-status >/dev/null 2>&1; then
        local pct
        pct=$(termux-battery-status 2>/dev/null | grep -o '"percentage":[[:space:]]*[0-9]*' | grep -o '[0-9]*' | head -1)
        if [ -n "$pct" ]; then echo "$pct"; return; fi
    fi
    echo "?"
}

# Uptime of a service (seconds) — via sv status
get_svc_uptime() {
    sv status "$1" 2>/dev/null | grep -oE '[0-9]+s' | head -1 | tr -d 's' || echo "0"
}

# Human-readable uptime from seconds
human_uptime() {
    local s="$1"
    if [ -z "$s" ] || [ "$s" = "0" ]; then echo "—"; return; fi
    local d=$((s / 86400)); s=$((s % 86400))
    local h=$((s / 3600)); s=$((s % 3600))
    local m=$((s / 60)); s=$((s % 60))
    if [ $d -gt 0 ]; then printf '%dd %dh %dm' $d $h $m
    elif [ $h -gt 0 ]; then printf '%dh %dm' $h $m
    elif [ $m -gt 0 ]; then printf '%dm %ds' $m $s
    else printf '%ds' $s
    fi
}

# Get Tailscale peers count (other devices in tailnet)
get_peer_count() {
    [ -S "$FS_SOCKET" ] || { echo "0"; return; }
    local n
    n=$(tailscale --socket="$FS_SOCKET" status 2>/dev/null | tail -n +2 | grep -c . 2>/dev/null | tr -d '[:space:]')
    echo "${n:-0}"
}

# Get Tailscale backend state (Running/Stopped/NeedsLogin)
get_ts_state() {
    [ -S "$FS_SOCKET" ] || { echo "no-socket"; return; }
    local status
    status=$(tailscale --socket="$FS_SOCKET" status 2>/dev/null | head -1)
    if echo "$status" | grep -q "100\."; then
        echo "running"
    else
        echo "stopped"
    fi
}
