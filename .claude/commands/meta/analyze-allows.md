---
description: ''
prompt: "# Analyze Claude Settings and Suggest Global Allows\n\nAnalyze all `.claude/settings.local.json`\
  \ files across my projects and home directory to identify permissions that should\
  \ be promoted to my global `~/.claude/settings.json` config.\n\n## Task\n\n1. **Discover\
  \ Local Settings Files**\n   - Search for all `settings.local.json` files under\
  \ `~/.claude-squad/` (worktrees)\n   - Search for all `settings.local.json` files\
  \ under `~/` (user projects)\n   - Exclude system directories and node_modules\n\
  \n2. **Extract and Aggregate Permissions**\n   - Parse each `settings.local.json`\
  \ file\n   - Extract all entries from the `permissions.allow` array\n   - Count\
  \ frequency of each permission across all files\n   - Track which projects use each\
  \ permission\n\n3. **Categorize Permissions by Safety Level**\n\n   **SAFE (Auto-recommend)**\
  \ - Read-only or non-destructive operations:\n   - `Read(*)` patterns for non-sensitive\
  \ files\n   - `Bash(ls:*)`, `Bash(pwd)`, `Bash(which:*)`, `Bash(head:*)`, `Bash(tail:*)`\n\
  \   - `Bash(go version)`, `Bash(node --version)`, `Bash(python --version)`\n   -\
  \ `Bash(go doc:*)`, `Bash(go list:*)`\n   - `Bash(git status)`, `Bash(git log:*)`,\
  \ `Bash(git show:*)`, `Bash(git diff:*)`\n   - `Glob(*)` patterns\n   - `Grep(*)`\
  \ patterns\n   - `WebFetch(domain:*)` for documentation sites\n   - MCP tools that\
  \ are read-only (browser_snapshot, get_*, list_*, search_*)\n\n   **MODERATE (Recommend\
  \ with note)** - Common dev operations, reversible:\n   - `Bash(npm install:*)`,\
  \ `Bash(npm test:*)`, `Bash(npm run:*)`\n   - `Bash(go build:*)`, `Bash(go test:*)`,\
  \ `Bash(go run:*)`\n   - `Bash(make:*)`, `Bash(docker:*)`\n   - `Bash(git add:*)`,\
  \ `Bash(git commit:*)`, `Bash(git push:*)`\n   - `Bash(curl:*)`, `Bash(jq:*)`\n\
  \   - `Bash(tmux:*)` commands\n   - MCP tools that modify (browser_click, browser_type,\
  \ create_*, update_*)\n\n   **CAUTION (Show but don't auto-recommend)** - Potentially\
  \ destructive:\n   - `Bash(rm:*)`, `Bash(kill:*)`, `Bash(killall:*)`, `Bash(pkill:*)`\n\
  \   - `Bash(kubectl delete:*)`\n   - `Bash(git reset:*)`, `Bash(git clean:*)`, `Bash(git\
  \ stash:*)` — can discard or hide local changes\n   - Very broad patterns like `Read(///**)`\
  \ or `Bash(*)`\n   - `SlashCommand(*)` patterns\n\n4. **Compare with Existing Global\
  \ Config**\n   - Read `~/.claude/settings.json`\n   - Identify which permissions\
  \ are already in the global allow list\n   - Filter out duplicates from recommendations\n\
  \n5. **Generate Recommendations Report**\n\n   Format the output as:\n\n   ```\n\
  \   ## Permissions Analysis Summary\n\n   - Total local settings files analyzed:\
  \ X\n   - Total unique permissions found: Y\n   - Already in global config: Z\n\
  \   - New recommendations: W\n\n   ## SAFE Permissions (Recommend Adding)\n\n  \
  \ | Permission | Frequency | Projects |\n   |------------|-----------|----------|\n\
  \   | Bash(go vet:*) | 5 | claude-squad, project-x, ... |\n\n   ## MODERATE Permissions\
  \ (Consider Adding)\n\n   | Permission | Frequency | Projects | Notes |\n   |------------|-----------|----------|-------|\n\
  \   | Bash(npm run build:*) | 3 | web-app, ui-lib | Build commands |\n\n   ## CAUTION\
  \ Permissions (Review Carefully)\n\n   | Permission | Frequency | Projects | Risk\
  \ |\n   |------------|-----------|----------|------|\n   | Bash(kill:*) | 2 | claude-squad\
  \ | Process termination |\n\n   ## Suggested Additions to ~/.claude/settings.json\n\
  \n   Copy these safe permissions to add:\n   ```json\n   [\n     \"Bash(go vet:*)\"\
  ,\n     \"Bash(go fmt:*)\",\n     ...\n   ]\n   ```\n   ```\n\n6. **Output Format\
  \ Options**\n   - If argument `$1` is \"json\", output machine-readable JSON\n \
  \  - If argument `$1` is \"apply\", show the commands to apply changes (but don't\
  \ execute)\n   - Default: Show the markdown report\n\n## Implementation Notes\n\n\
  - Use `find` to locate files, `jq` to parse JSON\n- Handle malformed JSON gracefully\
  \ (skip with warning)\n- Normalize permissions (remove trailing whitespace, etc.)\n\
  - Sort recommendations by frequency (most common first)\n- Shorten project paths\
  \ in output (show just directory name, not full path)\n\n"
---

# Analyze Claude Settings and Suggest Global Allows

Analyze all `.claude/settings.local.json` files across my projects and home directory to identify permissions that should be promoted to my global `~/.claude/settings.json` config.

## Task

1. **Discover Local Settings Files**
   - Search for all `settings.local.json` files under `~/.claude-squad/` (worktrees)
   - Search for all `settings.local.json` files under `~/` (user projects)
   - Exclude system directories and node_modules

2. **Extract and Aggregate Permissions**
   - Parse each `settings.local.json` file
   - Extract all entries from the `permissions.allow` array
   - Count frequency of each permission across all files
   - Track which projects use each permission

3. **Categorize Permissions by Safety Level**

   **SAFE (Auto-recommend)** - Read-only or non-destructive operations:
   - `Read(*)` patterns for non-sensitive files
   - `Bash(ls:*)`, `Bash(pwd)`, `Bash(which:*)`, `Bash(head:*)`, `Bash(tail:*)`
   - `Bash(go version)`, `Bash(node --version)`, `Bash(python --version)`
   - `Bash(go doc:*)`, `Bash(go list:*)`
   - `Bash(git status)`, `Bash(git log:*)`, `Bash(git show:*)`, `Bash(git diff:*)`
   - `Glob(*)` patterns
   - `Grep(*)` patterns
   - `WebFetch(domain:*)` for documentation sites
   - MCP tools that are read-only (browser_snapshot, get_*, list_*, search_*)

   **MODERATE (Recommend with note)** - Common dev operations, reversible:
   - `Bash(npm install:*)`, `Bash(npm test:*)`, `Bash(npm run:*)`
   - `Bash(go build:*)`, `Bash(go test:*)`, `Bash(go run:*)`
   - `Bash(make:*)`, `Bash(docker:*)`
   - `Bash(git add:*)`, `Bash(git commit:*)`, `Bash(git push:*)`
   - `Bash(curl:*)`, `Bash(jq:*)`
   - `Bash(tmux:*)` commands
   - MCP tools that modify (browser_click, browser_type, create_*, update_*)

   **CAUTION (Show but don't auto-recommend)** - Potentially destructive:
   - `Bash(rm:*)`, `Bash(kill:*)`, `Bash(killall:*)`, `Bash(pkill:*)`
   - `Bash(kubectl delete:*)`
   - `Bash(git reset:*)`, `Bash(git clean:*)`, `Bash(git stash:*)` — can discard or hide local changes
   - Very broad patterns like `Read(///**)` or `Bash(*)`
   - `SlashCommand(*)` patterns

4. **Compare with Existing Global Config**
   - Read `~/.claude/settings.json`
   - Identify which permissions are already in the global allow list
   - Filter out duplicates from recommendations

5. **Generate Recommendations Report**

   Format the output as:

   ```
   ## Permissions Analysis Summary

   - Total local settings files analyzed: X
   - Total unique permissions found: Y
   - Already in global config: Z
   - New recommendations: W

   ## SAFE Permissions (Recommend Adding)

   | Permission | Frequency | Projects |
   |------------|-----------|----------|
   | Bash(go vet:*) | 5 | claude-squad, project-x, ... |

   ## MODERATE Permissions (Consider Adding)

   | Permission | Frequency | Projects | Notes |
   |------------|-----------|----------|-------|
   | Bash(npm run build:*) | 3 | web-app, ui-lib | Build commands |

   ## CAUTION Permissions (Review Carefully)

   | Permission | Frequency | Projects | Risk |
   |------------|-----------|----------|------|
   | Bash(kill:*) | 2 | claude-squad | Process termination |

   ## Suggested Additions to ~/.claude/settings.json

   Copy these safe permissions to add:
   ```json
   [
     "Bash(go vet:*)",
     "Bash(go fmt:*)",
     ...
   ]
   ```
   ```

6. **Output Format Options**
   - If argument `$1` is "json", output machine-readable JSON
   - If argument `$1` is "apply", show the commands to apply changes (but don't execute)
   - Default: Show the markdown report

## Implementation Notes

- Use `find` to locate files, `jq` to parse JSON
- Handle malformed JSON gracefully (skip with warning)
- Normalize permissions (remove trailing whitespace, etc.)
- Sort recommendations by frequency (most common first)
- Shorten project paths in output (show just directory name, not full path)

