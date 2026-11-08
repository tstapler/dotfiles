#!/bin/bash
# PreToolUse(Bash) hook: before `gh pr create|ready|merge` (including env-prefixed
# and chained forms), inject a reminder to run the full adversarial review loop.
# PreToolUse so it lands before a chained `gh pr ready && gh pr merge` completes.
#
# Hot path: runs on EVERY Bash call, so it must not spawn anything. `read` is a
# builtin and `case` early-exits on the raw hook JSON; jq/grep run only on a hit.
IFS= read -r -d '' input
case $input in
  *"gh pr "*) ;;
  *) exit 0 ;;
esac
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""' 2>/dev/null)
if printf '%s' "$cmd" | grep -qE 'gh pr (create|ready|merge)'; then
  cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"MANDATORY REVIEW GATE (Tyler standing policy): you are about to open/ready/merge a PR. Before handing it to Tyler, marking it ready, or merging it you MUST run the full adversarial review loop — your own verified pass + fresh UNANCHORED reviewers across the right lenses (correctness, concurrency, domain-semantics vs the code being replaced, tests/security) + a round-2 convergence pass — and address every real finding. Bitbot + a glance is NOT enough. If this PR is docs/config-only, say so explicitly and scope the review lenses accordingly rather than skipping review."}}
JSON
fi
