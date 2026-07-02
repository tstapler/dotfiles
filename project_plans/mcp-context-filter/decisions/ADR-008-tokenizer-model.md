# ADR-008: Tokenizer Model for Token Count Metrics

Date: 2026-07-02
Status: DECISION PENDING - resolved by Task 1.7.1.0

## Decision Required

Which tiktoken model (cl100k_base or o200k_base) does Claude Code use for its context window measurement? This model must be used in mcp-proxy's TokenBudget calculations so that "tokens saved" in the proxy log matches "context window freed" as Claude Code sees it.

## Context

The success metric "reduce from ~42.6k to ≤10k tokens (>75% reduction)" is measured by tiktoken-rs. If the wrong model is used, the proxy may report 78% savings while Claude Code is seeing 12% savings — the headline metric would be meaningless.

The 42.6k baseline figure (~13,000 tokens for the 42-tool Atlassian server) was recorded empirically but the tokenizer used for that measurement is unconfirmed.

## Options

- cl100k_base (GPT-4, Claude 2 era)
- o200k_base (Claude 3+ era)

## Resolution

Task 1.7.1.0 (empirical test): run both encoders on a captured Atlassian tools/list JSON response. The model that matches the known ~13,000 token baseline within 5% is the correct model. Record result here and update Story 1.7.1 to use that model constant.

Update this ADR with result before beginning Task 1.7.1.1.
