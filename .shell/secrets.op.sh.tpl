# 1Password secret references for dotfiles

#
# Vault: "Personal" in the 'my' 1Password account (tystapler@gmail.com)
# To populate: run ~/.shell/setup_1password.sh (once, while old local.sh is still active)


# ── GitHub ────────────────────────────────────────────────────────────────────
export GITHUB_TOKEN="{{ op://FBG/GitHub PAT/credential }}"
export GITHUB_PERSONAL_ACCESS_TOKEN="{{ op://FBG/GitHub PAT/credential }}"

# ── Terraform Cloud ───────────────────────────────────────────────────────────
export TF_CLOUD_TOKEN="{{ op://FBG/Terraform Cloud/credential }}"

# ── Cloudflare ────────────────────────────────────────────────────────────────
export CLOUDFLARE_API_KEY="{{ op://FBG/Cloudflare/api_key }}"
export CLOUDFLARE_API_TOKEN="{{ op://FBG/Cloudflare/api_token }}"

# ── Datadog ───────────────────────────────────────────────────────────────────
export DATADOG_API_KEY="{{ op://FBG/Datadog/api_key }}"
export DD_API_KEY="{{ op://FBG/Datadog/api_key }}"
export DATADOG_APP_KEY="{{ op://FBG/Datadog/app_key }}"
export DD_APP_KEY="{{ op://FBG/Datadog/app_key }}"

# ── Twingate ──────────────────────────────────────────────────────────────────
export TWINGATE_API_TOKEN="{{ op://FBG/Twingate/credential }}"

# ── Artifactory ───────────────────────────────────────────────────────────────
export AMELCO_ARTIFACTORY_PASSWORD="{{ op://FBG/Artifactory/credential }}"

# ── Jira / Atlassian ──────────────────────────────────────────────────────────
export JIRA_TOKEN="{{ op://FBG/Jira/credential }}"
export ATLASSIAN_API_TOKEN="{{ op://FBG/Jira/credential }}"
export CONFLUENCE_API_TOKEN="{{ op://FBG/Jira/credential }}"
export JIRA_API_TOKEN="{{ op://FBG/Jira/credential }}"

# ── Slack ─────────────────────────────────────────────────────────────────────
export SLACK_TOKEN="{{ op://FBG/Slack Bot/credential }}"
export SLACK_MCP_XOXC_TOKEN="{{ op://FBG/Slack MCP/xoxc }}"
export SLACK_MCP_XOXD_TOKEN="{{ op://FBG/Slack MCP/xoxd }}"

# ── Okta ──────────────────────────────────────────────────────────────────────
export OKTA_TOKEN="{{ op://FBG/Okta/api_token }}"
export OKTA_CLIENT_SECRET="{{ op://FBG/Okta/client_secret }}"

# ── Geekbot ───────────────────────────────────────────────────────────────────
export GEEKBOT_TOKEN="{{ op://FBG/Geekbot/credential }}"

# ── Lacework ──────────────────────────────────────────────────────────────────
export LW_API_KEY="{{ op://FBG/Lacework/api_key }}"
export LW_API_SECRET="{{ op://FBG/Lacework/api_secret }}"

# ── AI APIs ───────────────────────────────────────────────────────────────────
export OPENAI_API_KEY="{{ op://FBG/OpenAI/credential }}"
export GEMINI_API_KEY="{{ op://FBG/Gemini/credential }}"
export OPENROUTER_API_KEY="{{ op://FBG/OpenRouter/credential }}"
export CLAUDE_CODE_OAUTH_TOKEN="{{ op://FBG/Claude/credential }}"

# ── PagerDuty ─────────────────────────────────────────────────────────────────
export PAGERDUTY_API_KEY="{{ op://FBG/PagerDuty/credential }}"

# ── Bitbucket ─────────────────────────────────────────────────────────────────
export BITBUCKET_TOKEN="{{ op://FBG/Bitbucket/credential }}"

# ── SonarCloud ────────────────────────────────────────────────────────────────
export SONAR_TOKEN="{{ op://FBG/SonarCloud/credential }}"

# ── Brave Search ─────────────────────────────────────────────────────────────
export BRAVE_API_KEY="{{ op://FBG/Brave Search/credential }}"

# ── Figma ─────────────────────────────────────────────────────────────────────
export FIGMA_TOKEN="{{ op://FBG/Figma/credential }}"
