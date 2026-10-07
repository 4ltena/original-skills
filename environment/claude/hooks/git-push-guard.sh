#!/usr/bin/env bash
# PreToolUse(Bash) guard for dangerous git push / gh delete operations.
#
# Splits the command into shell segments (&& || | |& ; & newline) and inspects
# ONLY git-push and gh-delete segments, tokenizing the push arguments. This
# avoids false decisions from unrelated tokens elsewhere in a compound command
# (e.g. `git branch -d`, `make -f`, a commit message containing "main").
#
# Decisions:
#   deny  — remote deletion (--delete / -d / leading-colon refspec; gh ... delete)
#   ask   — force push (--force / -f / combined short flag / +refspec) or a push
#           that targets main/master (explicit, or bare `git push` while on main)
# Silent otherwise, so ordinary commands follow the normal permission flow.
# Fails open on parse errors; the settings.json deny/ask globs remain a net.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
set -u
set -f   # disable globbing so refspec tokens like '*' are never expanded

input=$(cat 2>/dev/null) || exit 0
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null)
if [ -z "${cmd:-}" ]; then
  cmd=$(printf '%s' "$input" | python3 -c 'import sys,json
try:
    print(json.load(sys.stdin).get("tool_input",{}).get("command",""))
except Exception:
    pass' 2>/dev/null)
fi
[ -z "${cmd:-}" ] && exit 0

decision=""; reason=""
set_decision() { # $1=deny|ask  $2=reason ; deny outranks ask, never downgrade
  if [ "$1" = deny ]; then decision=deny; reason="$2"
  elif [ "$1" = ask ] && [ "$decision" != deny ]; then decision=ask; reason="$2"; fi
}

# Split compound command into segments, one per line.
segs=$(printf '%s' "$cmd" | sed -E 's/&&/\n/g; s/\|\|/\n/g; s/\|&/\n/g; s/;/\n/g; s/\|/\n/g; s/&/\n/g')

while IFS= read -r seg; do
  seg="${seg#"${seg%%[![:space:]]*}"}"   # ltrim
  seg="${seg%"${seg##*[![:space:]]}"}"   # rtrim
  [ -z "$seg" ] && continue

  # gh remote deletion -> deny
  if printf '%s' "$seg" | grep -Eq '(^|[[:space:]])gh[[:space:]]+(repo|release|secret|variable|gist|run)[[:space:]]+delete([[:space:]]|$)'; then
    set_decision deny "Remote deletion via gh is prohibited; it is never run automatically."
    continue
  fi

  # Strip git global options that can sit between 'git' and the subcommand
  # (-C <path>, -c <kv>, --git-dir/--work-tree/--namespace <v>), so forms like
  # `git -C /repo push origin main` are still recognized as a push.
  nseg=$(printf '%s' "$seg" | sed -E '
    s/(^|[[:space:]])-C[[:space:]]+[^[:space:]]+/\1/g;
    s/(^|[[:space:]])-c[[:space:]]+[^[:space:]]+/\1/g;
    s/(^|[[:space:]])--git-dir[=[:space:]]+[^[:space:]]+/\1/g;
    s/(^|[[:space:]])--work-tree[=[:space:]]+[^[:space:]]+/\1/g;
    s/(^|[[:space:]])--namespace[=[:space:]]+[^[:space:]]+/\1/g')

  # only inspect git push segments
  printf '%s' "$nseg" | grep -Eq '(^|[[:space:]])git[[:space:]]+push([[:space:]]|$)' || continue

  rest=$(printf '%s' "$nseg" | sed -E 's/^.*git[[:space:]]+push//')
  force=0; del=0; mainp=0; nonflag=0
  for tok in $rest; do
    case "$tok" in
      --force*)  force=1 ;;
      --delete*) del=1 ;;
      --*)       : ;;
      -*)  case "$tok" in *f*) force=1 ;; esac
           case "$tok" in *d*) del=1 ;; esac ;;
      :*)  del=1; nonflag=$((nonflag+1)) ;;
      *)   nonflag=$((nonflag+1)); t="$tok"
           case "$t" in +*) force=1; t="${t#+}" ;; esac
           dst="${t##*:}"
           case "$t"   in main|master) mainp=1 ;; esac
           case "$dst" in main|master|refs/heads/main|refs/heads/master) mainp=1 ;; esac ;;
    esac
  done

  if [ "$del" = 1 ]; then
    set_decision deny "Remote branch/tag deletion is prohibited."
    continue
  fi
  [ "$force" = 1 ] && set_decision ask "Force push requires explicit approval (allowed only on explicit instruction)."
  [ "$mainp" = 1 ] && set_decision ask "Direct push to main/master is gated; use a working branch and a PR."

  # bare-ish push (no explicit refspec target): gate when on main/master
  if [ "$mainp" = 0 ] && [ "$nonflag" -le 1 ]; then
    cur=$(git branch --show-current 2>/dev/null)
    if [ "${cur:-}" = main ] || [ "${cur:-}" = master ]; then
      set_decision ask "On '$cur': auto-push is limited to working branches; use a branch and a PR."
    fi
  fi
done <<EOF
$segs
EOF

if [ -n "$decision" ]; then
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"%s","permissionDecisionReason":"%s"}}\n' "$decision" "$reason"
fi
exit 0
