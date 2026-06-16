# Personal 1Password secret references
# Vault: "Personal" in my.1password.com (tystapler@gmail.com)
#
# To bootstrap on a new machine, first create the secure note in 1Password (one time):
#   op item create --category="Secure Note" --title="Personal Shell Secrets Template" \
#     --vault="Personal" --account=my.1password.com \
#     "notesPlain=$(cat ~/.shell/secrets.op.sh.tpl)"
# Then on new machines:
#   eval "$(op signin --account my.1password.com)"
#   op read "op://Personal/Personal Shell Secrets Template/notesPlain" \
#     --account my.1password.com > ~/.shell/secrets.op.sh.tpl

# ── Anthropic ─────────────────────────────────────────────────────────────────
export ANTHROPIC_API_KEY="{{ op://Personal/Anthropic/credential }}"
