#!/bin/bash
# JSONL Run-Logging Helper nach geodata-plugin-standard §7.4.
#
# Muss in derselben Shell gesourct werden, deren EXIT geloggt werden soll
# (run_log_init registriert einen `trap … EXIT`). Erwartet scripts/ci/utils.sh
# bereits geladen (log_warn) — best-effort: Schreibfehler nach GEODATA_LOG_DIR
# (Default /var/log) brechen den Lauf nie ab, der ursprüngliche Exit-Code
# bleibt erhalten.
#
# API:
#   run_log_file <name>                # -> ${GEODATA_LOG_DIR:-/var/log}/<name>
#   run_log_init <history.jsonl> <status.json>
#   run_log_str  <key> <value>         # Extra-Feld: escapter String
#   run_log_num  <key> <value>         # Extra-Feld: Zahl (nicht-numerisch -> null)
#   run_log_raw  <key> <json>          # Extra-Feld: roher JSON-Wert (Bool, Array, …)
# Vor regulärem Ende setzen:
#   RUN_LOG_STATUS="ok"; RUN_LOG_MESSAGE="…"; RUN_LOG_ERROR=""   # leerer error -> null

if ! command -v log_warn >/dev/null 2>&1; then
    log_warn() { echo "  ⚠ $1" >&2; }
fi

_RUN_LOG_HISTORY=""
_RUN_LOG_STATUS_FILE=""
_RUN_LOG_START_TS=0
_RUN_LOG_EXTRA_KEYS=()
_RUN_LOG_EXTRA_JSON=()

RUN_LOG_STATUS="error"
RUN_LOG_MESSAGE=""
RUN_LOG_ERROR="Lauf abgebrochen (kein reguläres Ende)."

run_log_file() {
    echo "${GEODATA_LOG_DIR:-/var/log}/$1"
}

_run_log_json_escape() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/}"
    s="${s//$'\t'/\\t}"
    printf '%s' "$s"
}

run_log_str() {
    _RUN_LOG_EXTRA_KEYS+=("$1")
    _RUN_LOG_EXTRA_JSON+=("\"$(_run_log_json_escape "$2")\"")
}

run_log_num() {
    local key="$1" value="$2"
    if [[ "$value" =~ ^-?[0-9]+([.][0-9]+)?$ ]]; then
        _RUN_LOG_EXTRA_KEYS+=("$key")
        _RUN_LOG_EXTRA_JSON+=("$value")
    else
        _RUN_LOG_EXTRA_KEYS+=("$key")
        _RUN_LOG_EXTRA_JSON+=("null")
    fi
}

run_log_raw() {
    _RUN_LOG_EXTRA_KEYS+=("$1")
    _RUN_LOG_EXTRA_JSON+=("$2")
}

_run_log_write() {
    # Muss best-effort bleiben: darf den (bereits feststehenden) Exit-Code
    # des Laufs nicht überschreiben, egal was hier schiefgeht.
    local exit_code=$?
    local ts duration msg_json err_json line i

    ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    duration=$(( $(date +%s) - _RUN_LOG_START_TS ))
    msg_json="\"$(_run_log_json_escape "$RUN_LOG_MESSAGE")\""
    if [ -z "$RUN_LOG_ERROR" ]; then
        err_json="null"
    else
        err_json="\"$(_run_log_json_escape "$RUN_LOG_ERROR")\""
    fi

    line="{\"timestamp\":\"$ts\",\"status\":\"$(_run_log_json_escape "$RUN_LOG_STATUS")\",\"duration_seconds\":$duration"
    for i in "${!_RUN_LOG_EXTRA_KEYS[@]}"; do
        line+=",\"${_RUN_LOG_EXTRA_KEYS[$i]}\":${_RUN_LOG_EXTRA_JSON[$i]}"
    done
    line+=",\"message\":$msg_json,\"error\":$err_json}"

    if ! mkdir -p "$(dirname "$_RUN_LOG_HISTORY")" 2>/dev/null || ! printf '%s\n' "$line" >>"$_RUN_LOG_HISTORY" 2>/dev/null; then
        log_warn "Konnte Run-Log nicht nach $_RUN_LOG_HISTORY schreiben (best-effort, Ergebnis des Laufs bleibt unverändert)."
    elif ! printf '%s\n' "$line" >"$_RUN_LOG_STATUS_FILE" 2>/dev/null; then
        log_warn "Konnte Status-Datei nicht nach $_RUN_LOG_STATUS_FILE schreiben (best-effort)."
    fi

    return "$exit_code"
}

run_log_init() {
    _RUN_LOG_HISTORY="$1"
    _RUN_LOG_STATUS_FILE="$2"
    _RUN_LOG_START_TS=$(date +%s)
    trap _run_log_write EXIT
}
