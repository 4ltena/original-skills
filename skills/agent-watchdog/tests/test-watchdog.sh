#!/usr/bin/env bash
# End-to-end tests for the Codex watchdog. No real Codex process is started.
set -u

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
HOOK="${CODEX_WATCHDOG_HOOK:-$HOME/.codex/hooks/agent-watchdog.sh}"
SUP="$ROOT/scripts/codex-exec-watchdog.sh"
TMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/agent-watchdog-test.XXXXXX") || exit 1
trap 'rm -rf -- "$TMP_ROOT"' EXIT
PASS=0
FAIL=0

ok() { PASS=$((PASS + 1)); printf 'PASS: %s\n' "$1"; }
bad() { FAIL=$((FAIL + 1)); printf 'FAIL: %s\n' "$1"; }
check() {
  if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (expected [$2], got [$3])"; fi
}

payload() {
  jq -cn --arg s "$1" --arg a "$2" \
    '{hook_event_name:"SubagentStop",session_id:$s,agent_id:$a,agent_type:"worker",last_assistant_message:null}'
}

normal='{"hook_event_name":"SubagentStop","session_id":"normal","agent_id":"one","last_assistant_message":"done"}'
out=$(printf '%s' "$normal" | TMPDIR="$TMP_ROOT" "$HOOK")
check "normal stop is silent" "" "$out"

mkdir "$TMP_ROOT/state-failure"
: >"$TMP_ROOT/state-failure/codex-agent-watchdog"
out=$(payload state-failure one | TMPDIR="$TMP_ROOT/state-failure" "$HOOK")
check "state directory failure does not continue" "" "$(printf '%s' "$out" | jq -r '.decision // empty')"
printf '%s' "$out" | jq -r '.systemMessage // empty' | grep -q 'cannot create retry state directory' \
  && ok "state directory failure escalates" || bad "state directory failure did not escalate: $out"

FAKE_DIR="$TMP_ROOT/fake"
mkdir "$FAKE_DIR"
export FAKE_DIR
cat >"$FAKE_DIR/codex" <<'EOF'
#!/usr/bin/env bash
case "$(cat "$FAKE_DIR/scenario")" in
  success)
    echo '{"type":"thread.started","thread_id":"11111111-1111-1111-1111-111111111111"}'
    echo '{"type":"item.completed","item":{"type":"agent_message","text":"done"}}'
    echo '{"type":"turn.completed"}'
    ;;
  failure)
    echo '{"type":"thread.started","thread_id":"22222222-2222-2222-2222-222222222222"}'
    echo '{"type":"error","message":"permission denied"}'
    exit 1
    ;;
esac
EOF
chmod +x "$FAKE_DIR/codex"
export CODEX_BIN="$FAKE_DIR/codex" WATCHDOG_POLL=1 WATCHDOG_BACKOFFS="0 0"

mkdir "$TMP_ROOT/success-tmp"
echo success >"$FAKE_DIR/scenario"
out=$(TMPDIR="$TMP_ROOT/success-tmp" "$SUP" -- "bounded task" 2>"$FAKE_DIR/success.err")
check "successful run exits zero" "0" "$?"
check "successful run returns final message" "done" "$out"
count=$(find "$TMP_ROOT/success-tmp" -maxdepth 1 -type d -name 'codex-exec-watchdog.*' | wc -l | tr -d ' ')
check "successful run removes temporary directory" "0" "$count"

mkdir "$TMP_ROOT/failure-tmp"
echo failure >"$FAKE_DIR/scenario"
TMPDIR="$TMP_ROOT/failure-tmp" "$SUP" -- "bounded task" >"$FAKE_DIR/failure.out" 2>"$FAKE_DIR/failure.err"
check "deterministic failure exits one" "1" "$?"
log_dir=$(sed -n 's/^  attempt logs : //p' "$FAKE_DIR/failure.err" | tail -1)
[ -n "$log_dir" ] && [ -d "$log_dir" ] \
  && ok "failed run retains evidence directory" || bad "failed run did not retain evidence: $log_dir"

printf 'RESULT: %s passed, %s failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
