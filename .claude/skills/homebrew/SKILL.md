---
name: homebrew
description: Install, manage, and troubleshoot macOS packages using Homebrew. Use when a required tool is missing, needs updating, or when managing taps, casks, or formula versions.
---

# Homebrew Package Management

Use Homebrew for all macOS software installation and management.

## When to Use

**Use this skill for:**
- Installing missing CLI tools or applications
- Updating or upgrading packages
- Managing taps (third-party formula sources)
- Troubleshooting formula conflicts or version issues
- Checking what's installed

**Don't use for:**
- Python packages → use `uv` or `pip`
- Node packages → use `npm` / `pnpm`
- Language-specific package managers in general

## Installing a Missing Tool

When a tool is not found, follow this workflow:

### 1. Check if Already Installed

```bash
brew list --formula | grep <tool>
which <tool>
```

### 2. Search for the Formula

```bash
brew search <tool>
```

If not found via `brew search`, use **WebSearch** to find the correct formula name or tap:

```
Search: "install <tool> homebrew" OR "brew tap <tool>"
```

### 3. Install

```bash
# Standard formula
brew install <formula>

# Cask (GUI apps)
brew install --cask <cask>

# From a tap
brew tap <org>/<repo>
brew install <org>/<repo>/<formula>
```

### 4. Verify Installation

```bash
which <tool>
<tool> --version
```

## Common Operations

| Task | Command |
|------|---------|
| Install package | `brew install <formula>` |
| Install GUI app | `brew install --cask <app>` |
| Update Homebrew | `brew update` |
| Upgrade all packages | `brew upgrade` |
| Upgrade one package | `brew upgrade <formula>` |
| Uninstall | `brew uninstall <formula>` |
| List installed | `brew list` |
| Search | `brew search <term>` |
| Info/version | `brew info <formula>` |
| Fix issues | `brew doctor` |
| Add tap | `brew tap <org>/<repo>` |

## Key Formulas for This Workflow

| Tool | Formula | Purpose |
|------|---------|---------|
| ast-grep | `brew install ast-grep` | Semantic code search |
| grit | `brew install gritql` | AST-based refactoring |
| gh | `brew install gh` | GitHub CLI |
| jj | `brew install jj` | Jujutsu VCS |
| uv | `brew install uv` | Python package manager |

## Troubleshooting

**Formula not found:**
```bash
brew update && brew search <term>
# If still not found, use WebSearch to find the tap
```

**Permission errors:**
```bash
brew doctor  # Diagnose issues
```

**Version conflicts:**
```bash
brew info <formula>  # Shows available versions
brew install <formula>@<version>  # Install specific version
brew link --overwrite <formula>  # Force link
```

**Outdated Homebrew:**
```bash
brew update && brew upgrade
```
