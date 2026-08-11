Call request_review with item_id=a31407ce-29de-45d1-902e-c5a4026197d4 and a 2-3 sentence summary of what was built.

Do NOT end your session after this. Wait a bit, then call get_backlog_item (or /backlog/status) again — the verdict appears under "Latest Review Verdict" once the reviewer submits it.

PASS → run /backlog/ship now to open the pull request yourself (it drives /github:pr-ship through local CI, code review, remote CI, and merge-conflict resolution) — do not stop here; shipping the PR is part of this task, not a separate step someone else does.

FAIL/PARTIAL → fix the noted gaps in this same session and run /backlog/review again. Keep count of how many times you've run /backlog/review in THIS session (count your own calls in this conversation — nothing tracks it for you). After 3 review cycles without a PASS, STOP looping: run /backlog/ship anyway to open a PR so a human can pick up the review directly, rather than retrying /backlog/review again.
