#!/usr/bin/env bash
# codex-exec-watchdog.sh — run one `codex exec` task under the agent-watchdog policy.
#
# Wraps a non-interactive Codex run: detects failure (non-zero exit, no
# turn.completed event) and stalls (no new output for --stall-timeout seconds,
# then the process tree is killed), and resumes THE SAME session with
# `codex exec resume <thread_id>`. The default is one automatic retry (two total
# attempts). A third total attempt is allowed only when the second failure is
# positively classified as transient. Deterministic or unsafe work is never
# resumed automatically.
#
# Exit 0: success; the subagent's final message is printed to stdout.
# Exit 1: escalation after the cap / deterministic failure; report on stderr,
#         attempt logs are kept for inspection.
# Exit 2: usage error.
#
# Usage:
#   codex-exec-watchdog.sh [--max-attempts N] [--stall-timeout SEC] \
#                          -- [codex exec flags...] "<prompt>"
#   e.g. codex-exec-watchdog.sh -- -C "$repo" --skip-git-repo-check "run the tests"
#
# The LAST argument after -- must be the prompt. Flags are passed to the fresh
# `codex exec` run; only flags that `codex exec resume` also accepts (-c, -m,
# --enable/--disable, --strict-config, --skip-git-repo-check, --ignore-*,
# --dangerously-bypass-*) are forwarded to resume attempts as well. --json is
# added by this script; --ephemeral is rejected (an unrecorded session cannot
# be resumed). Note that `codex exec resume` does not accept -C: resumes run
# from THIS script's cwd, so pair -C with --skip-git-repo-check or launch the
# watchdog from inside the target repo.
#
# Env seams (mainly for the self-test):
#   CODEX_BIN           codex binary to run (default: codex)
#   WATCHDOG_POLL       stall-poll interval seconds (default: 5)
#   WATCHDOG_BACKOFFS   space-separated backoff seconds (default: "5 15")

set -u
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"

MAX_ATTEMPTS=2
STALL_TIMEOUT=600
CODEX_BIN="${CODEX_BIN:-codex}"
POLL="${WATCHDOG_POLL:-5}"
read -r -a BACKOFFS <<<"${WATCHDOG_BACKOFFS:-5 15}"

usage_err() {
  echo "codex-exec-watchdog: $1" >&2
  exit 2
}

numeric() { case "$1" in '' | *[!0-9]*) return 1 ;; *) return 0 ;; esac; }

while [ $# -gt 0 ]; do
  case "$1" in
    --max-attempts)
      [ $# -ge 2 ] || usage_err "missing value for --max-attempts"
      numeric "$2" && [ "$2" -ge 1 ] && [ "$2" -le 3 ] || usage_err "--max-attempts needs an integer from 1 to 3"
      MAX_ATTEMPTS="$2"; shift 2 ;;
    --stall-timeout)
      [ $# -ge 2 ] || usage_err "missing value for --stall-timeout"
      numeric "$2" && [ "$2" -ge 1 ] || usage_err "--stall-timeout needs an integer >= 1"
      STALL_TIMEOUT="$2"; shift 2 ;;
    --) shift; break ;;
    *) usage_err "unknown option: $1 (args after -- go to codex exec)" ;;
  esac
done
[ $# -gt 0 ] || usage_err "no codex exec arguments given (the last one must be the prompt)"

# Split the codex args: last arg = prompt; classify the flags before it.
# fresh_flags go to the initial `codex exec`; resume_flags only contains flags
# `codex exec resume` also accepts (verified against codex-cli 0.143.0 --help).
prompt="${!#}"
auto_retry_safe=1
fresh_flags=() resume_flags=()
add_both() { fresh_flags+=("$@"); resume_flags+=("$@"); }
i=1
n=$(($# - 1))
while [ $i -le $n ]; do
  a="${!i}"
  case "$a" in
    --json) ;; # this script adds --json itself
    --ephemeral) usage_err "--ephemeral is incompatible with the watchdog (an unrecorded session cannot be resumed)" ;;
    -c | --config | -m | --model | --enable | --disable | -o | --output-last-message | --output-schema)
      j=$((i + 1)); [ $j -le $n ] || usage_err "missing value for $a (or the prompt is missing as the last argument)"
      add_both "$a" "${!j}"; i=$j ;;
    --config=* | --model=* | --enable=* | --disable=* | --output-last-message=* | --output-schema=*)
      add_both "$a" ;;
    --strict-config | --skip-git-repo-check | --ignore-user-config | --ignore-rules | \
      --dangerously-bypass-approvals-and-sandbox | --dangerously-bypass-hook-trust)
      add_both "$a" ;;
    -i | --image | -C | --cd | --add-dir | -s | --sandbox | -p | --profile | --local-provider)
      j=$((i + 1)); [ $j -le $n ] || usage_err "missing value for $a (or the prompt is missing as the last argument)"
      fresh_flags+=("$a" "${!j}"); i=$j ;;
    *) fresh_flags+=("$a") ;; # unknown flag: fresh run only (safest)
  esac
  i=$((i + 1))
done

# Run the initial command, but never auto-resume work whose prompt or flags may
# repeat an approval-gated/destructive side effect.
prompt_lc=$(printf '%s' "$prompt" | tr '[:upper:]' '[:lower:]')
if printf '%s' "$prompt_lc" | grep -Eq 'force[- ]?push|git push|remote delet|reset --hard|clean -fdx|release (publish|publication)|gh release create|merge.+(main|master)|requires? approval|ask for approval'; then
  auto_retry_safe=0
fi
for a in ${fresh_flags[@]+"${fresh_flags[@]}"}; do
  case "$a" in --dangerously-bypass-approvals-and-sandbox | --dangerously-bypass-hook-trust) auto_retry_safe=0 ;; esac
done

workdir=$(mktemp -d "${TMPDIR:-/tmp}/codex-exec-watchdog.XXXXXX") || exit 2

cleanup_success() {
  case "$workdir" in
    "${TMPDIR:-/tmp}"/codex-exec-watchdog.*) rm -rf -- "$workdir" ;;
    *) echo "codex-exec-watchdog: refusing to clean unexpected path: $workdir" >&2; return 1 ;;
  esac
}

kill_tree() { # $1 = pid, $2 = signal — kill descendants first, then the pid
  local c
  for c in $(pgrep -P "$1" 2>/dev/null); do kill_tree "$c" "$2"; done
  kill "-$2" "$1" 2>/dev/null
}

pid=""
trap '[ -n "$pid" ] && kill_tree "$pid" TERM; exit 130' INT TERM

thread_id=""
prev_sig=""
fail_reason=""

for ((attempt = 1; attempt <= MAX_ATTEMPTS; attempt++)); do
  if [ "$attempt" -gt 1 ]; then
    backoff="${BACKOFFS[$((attempt - 2))]:-45}"
    echo "codex-exec-watchdog: attempt $((attempt - 1)) failed ($fail_reason); retrying in ${backoff}s..." >&2
    sleep "$backoff"
  fi

  log="$workdir/attempt-$attempt.jsonl"
  errlog="$workdir/attempt-$attempt.stderr"

  if [ "$attempt" -eq 1 ]; then
    "$CODEX_BIN" exec --json ${fresh_flags[@]+"${fresh_flags[@]}"} "$prompt" >"$log" 2>"$errlog" &
  else
    "$CODEX_BIN" exec resume "$thread_id" --json ${resume_flags[@]+"${resume_flags[@]}"} \
      "agent-watchdog resume (attempt $attempt of $MAX_ATTEMPTS): the previous non-interactive run was interrupted ($fail_reason). Continue the ORIGINAL task from where it left off; if it is already complete, output the final summary. Never repeat approval-gated or destructive actions (push, remote deletion, reset --hard, release publish)." \
      >"$log" 2>"$errlog" &
  fi
  pid=$!

  # Stall watch: kill the process tree when no bytes arrive for STALL_TIMEOUT.
  stalled=0 idle=0 last_total=0
  {
    while kill -0 "$pid" 2>/dev/null; do
      sleep "$POLL"
      total=$(($(wc -c <"$log" 2>/dev/null || echo 0) + $(wc -c <"$errlog" 2>/dev/null || echo 0)))
      if [ "$total" -gt "$last_total" ]; then
        last_total=$total idle=0
      else
        idle=$((idle + POLL))
      fi
      if [ "$idle" -ge "$STALL_TIMEOUT" ]; then
        stalled=1
        kill_tree "$pid" TERM
        sleep 2
        kill_tree "$pid" KILL
        break
      fi
    done
    wait "$pid"
  } 2>/dev/null
  rc=$?
  pid=""

  [ -n "$thread_id" ] || thread_id=$(jq -r 'select(.type == "thread.started") | .thread_id' "$log" 2>/dev/null | head -1)

  if [ "$stalled" -eq 0 ] && [ "$rc" -eq 0 ] && grep -q '"type":"turn.completed"' "$log"; then
    final=$(jq -rs 'map(select(.type == "item.completed") | .item | select(.type == "agent_message") | .text) | last // empty' "$log" 2>/dev/null)
    if [ -n "$final" ]; then
      printf '%s\n' "$final"
    else
      echo "codex-exec-watchdog: run succeeded but no final agent message could be extracted" >&2
    fi
    cleanup_success || exit 1
    exit 0
  fi

  # Classify failures before authorizing a retry. Unknown safe failures get the
  # single default retry; only a positive transient classification gets another.
  sig_line=$(grep -E '"type":"(error|turn\.failed)"' "$log" | tail -1)
  sig=""
  err_tail=""
  failure_kind="unknown"
  if [ "$stalled" -eq 1 ]; then
    fail_reason="stalled: no output for ${STALL_TIMEOUT}s, process tree killed"
    failure_kind="transient"
  elif [ -n "$sig_line" ]; then
    fail_reason="error event: $(printf '%s' "$sig_line" | head -c 200)"
    sig=$(printf '%s' "$sig_line" | shasum -a 256 | cut -d' ' -f1)
  else
    err_tail=$(grep -v '^[[:space:]]*$' "$errlog" 2>/dev/null | tail -1 | head -c 200)
    fail_reason="exit code $rc without turn.completed${err_tail:+ (stderr: $err_tail)}"
    sig=$(printf 'exit=%s:%s' "$rc" "$err_tail" | shasum -a 256 | cut -d' ' -f1)
  fi

  detail_lc=$(printf '%s %s' "$sig_line" "${err_tail:-}" | tr '[:upper:]' '[:lower:]')
  if printf '%s' "$detail_lc" | grep -Eq 'cancell?ed[_ -]?by[_ -]?user|user[_ -]?(stop|cancel)|interrupted[_ -]?by[_ -]?user'; then
    failure_kind="user-stop"
  elif printf '%s' "$detail_lc" | grep -Eq 'tim(e|ed)[ -]?out|timeout|rate[ -]?limit|temporar(il)?y unavailable|service unavailable|connection (reset|refused|closed)|network error|broken pipe'; then
    failure_kind="transient"
  elif printf '%s' "$detail_lc" | grep -Eq 'invalid (argument|input|option)|unsupported|permission denied|unauthori[sz]ed|forbidden|authentication failed|syntax error|compile error|test(s)? failed|command not found|no such file'; then
    failure_kind="deterministic"
  fi

  if [ "$auto_retry_safe" -ne 1 ]; then
    fail_reason="$fail_reason; automatic retry withheld for approval-gated or destructive work"
    break
  fi
  if [ "$failure_kind" = "user-stop" ]; then
    fail_reason="$fail_reason; user stop detected"
    break
  fi
  if [ "$failure_kind" = "deterministic" ]; then
    echo "codex-exec-watchdog: deterministic failure — not retrying." >&2
    break
  fi

  if [ -n "$sig" ] && [ "$sig" = "$prev_sig" ]; then
    echo "codex-exec-watchdog: deterministic failure (identical signature on consecutive attempts) — stopping early." >&2
    break
  fi
  prev_sig="$sig"

  # A third total attempt is the one exceptional retry and requires a positive
  # transient classification. Never redispatch a failed fresh run: continuation
  # requires both a captured thread and CLI resume support.
  if [ "$attempt" -ge 2 ] && [ "$failure_kind" != "transient" ]; then
    echo "codex-exec-watchdog: additional retry withheld; failure is not positively transient." >&2
    break
  fi
  if [ "$attempt" -lt "$MAX_ATTEMPTS" ]; then
    if [ -z "$thread_id" ]; then
      fail_reason="$fail_reason; no thread id captured for safe continuation"
      break
    fi
    if ! "$CODEX_BIN" exec resume --help >/dev/null 2>&1; then
      fail_reason="$fail_reason; installed Codex CLI does not expose exec resume"
      break
    fi
  fi
done

{
  echo "codex-exec-watchdog: ESCALATION — task did not complete."
  echo "  last failure : ${fail_reason:-<none recorded>}"
  echo "  thread id    : ${thread_id:-<none captured>}"
  echo "  attempt logs : $workdir"
  [ -n "$thread_id" ] && echo "  inspect with : codex exec resume $thread_id \"report current state\""
} >&2
exit 1
