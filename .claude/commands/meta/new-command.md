---
description: Guide through creating a new Claude Code slash command with proper hierarchy
  and location
prompt: "# Creating a new Claude Code slash command: `{{args}}`\n\nI'll guide you\
  \ through creating a new Claude Code slash command based on the specified command\
  \ name and type.\n\n## Command Hierarchy and Locations\n\nClaude Code supports different\
  \ types of slash commands with specific locations and visibility:\n\n1. **Project\
  \ Commands** (shared with team)\n   - Location: `.claude/commands/` (in project\
  \ directory)\n   - Visible to: Anyone with access to the repository\n   - Marked\
  \ as: \"(project)\" in `/help`\n   - Use for: Project-specific workflows, team conventions,\
  \ shared templates\n\n2. **Personal Commands** (available across all projects)\n\
  \   - Location: `~/.claude/commands/` (in home directory)\n   - Visible to: Only\
  \ you, on your machine\n   - Marked as: \"(user)\" in `/help`\n   - Use for: Personal\
  \ preferences, workflows you use across projects\n\n3. **Namespaced Commands** (organizational\
  \ structure)\n   - Use subdirectories to create command namespaces\n   - Example:\
  \ `.claude/commands/frontend/component.md` creates `/frontend:component`\n   - Helps\
  \ organize related commands into logical groups\n\n## Creating Your Command\n\n\
  Let's create a new command based on your inputs:\n\nCommand Name: `${1:-example_command}`\n\
  Command Type: `${2:-personal}` (Options: project, personal)\nCommand Description:\
  \ `${3:-A helpful command for Claude Code}`\n\n### Steps to Create This Command:\n\
  \n1. **Choose the correct directory** based on command type:\n   - Project command:\
  \ `.claude/commands/` (in current project)\n   - Personal command: `~/.claude/commands/`\
  \ (in your home directory)\n\n2. **Create the command file**:\n   ```bash\n   #\
  \ For project command:\n   mkdir -p .claude/commands\n   touch .claude/commands/${1:-example_command}.md\n\
  \   \n   # For personal command:\n   mkdir -p ~/.claude/commands\n   touch ~/.claude/commands/${1:-example_command}.md\n\
  \   ```\n\n3. **Edit the command file** with your desired prompt content:\n   The\
  \ file should contain the text you want Claude to process when the command is invoked.\n\
  \n4. **Optional: Add YAML frontmatter** for additional metadata:\n   ```yaml\n \
  \  ---\n   title: ${1:-Example Command}\n   description: ${3:-A helpful command\
  \ for Claude Code}\n   arguments: [arg1, arg2] # Optional arguments the command\
  \ accepts\n   ---\n   ```\n\n5. **Add argument support** with `{{args}}` or numbered\
  \ variables:\n   - Use `{{args}}` to access all arguments as a single string\n \
  \  - Use `$1`, `$2`, etc. to access specific arguments\n   - Use `${1:-default}`\
  \ to provide default values\n\n## Example Command Structure\n\nHere's an example\
  \ structure for your new `/${1:-example_command}` command:\n\n```markdown\n---\n\
  title: ${1:-Example Command}\ndescription: ${3:-A helpful command for Claude Code}\n\
  arguments: [arg1, arg2]\n---\n\n# ${1:-Example Command}\n\nThis is the content of\
  \ your command. When you invoke /${1:-example_command},\nClaude will process this\
  \ text as a prompt.\n\nYou can reference arguments:\n- First argument: $1\n- Second\
  \ argument: $2\n- All arguments: {{args}}\n\n## Using This Command\n\nExplain how\
  \ to use this command effectively.\n```\n\n## Using Your New Command\n\nOnce created,\
  \ you can invoke your command by typing:\n`/${1:-example_command} [arguments]`\n\
  \nThe command will be available:\n- Project commands: Only in the specific project\n\
  - Personal commands: In all your Claude Code conversations\n\n## Advanced Features\n\
  \n1. **File references**:\n   ```\n   Please analyze the code in @path/to/file.js\n\
  \   ```\n\n2. **Bash command execution**:\n   ```\n   Results of running a command:\n\
  \   \\`\\`\\`bash\n   ls -la\n   \\`\\`\\`\n   ```\n\n3. **Command nesting**:\n\
  \   You can invoke other commands from within a command.\n\n## Command Template\
  \ Based on Your Inputs\n\nHere's a template for your new `/${1:-example_command}`\
  \ command that incorporates your description:\n\n```markdown\n---\ntitle: ${1:-Example\
  \ Command}\ndescription: ${3:-A helpful command for Claude Code}\narguments: [arg1,\
  \ arg2]\n---\n\n# ${1:-Example Command}\n\n${3:-A helpful command for Claude Code}\n\
  \nThis command was created to help with specific tasks related to this purpose.\n\
  \n## Usage\n\nHow to use this command:\n/${1:-example_command} [arguments]\n\n##\
  \ Implementation\n\nThe command will execute the following:\n\n1. Step one\n2. Step\
  \ two\n3. Step three\n\n```\n\nWould you like me to create this command file for\
  \ you now? If so, please confirm the command name (`$1`), type (`$2`), and description\
  \ (`$3`) I should use.\n"
---

# Creating a new Claude Code slash command: `$ARGUMENTS`

I'll guide you through creating a new Claude Code slash command based on the specified command name and type.

## Command Hierarchy and Locations

Claude Code supports different types of slash commands with specific locations and visibility:

1. **Project Commands** (shared with team)
   - Location: `.claude/commands/` (in project directory)
   - Visible to: Anyone with access to the repository
   - Marked as: "(project)" in `/help`
   - Use for: Project-specific workflows, team conventions, shared templates

2. **Personal Commands** (available across all projects)
   - Location: `~/.claude/commands/` (in home directory)
   - Visible to: Only you, on your machine
   - Marked as: "(user)" in `/help`
   - Use for: Personal preferences, workflows you use across projects

3. **Namespaced Commands** (organizational structure)
   - Use subdirectories to create command namespaces
   - Example: `.claude/commands/frontend/component.md` creates `/frontend:component`
   - Helps organize related commands into logical groups

## Creating Your Command

Let's create a new command based on your inputs:

Command Name: `${1:-example_command}`
Command Type: `${2:-personal}` (Options: project, personal)
Command Description: `${3:-A helpful command for Claude Code}`

### Steps to Create This Command:

1. **Choose the correct directory** based on command type:
   - Project command: `.claude/commands/` (in current project)
   - Personal command: `~/.claude/commands/` (in your home directory)

2. **Create the command file**:
   ```bash
   # For project command:
   mkdir -p .claude/commands
   touch .claude/commands/${1:-example_command}.md
   
   # For personal command:
   mkdir -p ~/.claude/commands
   touch ~/.claude/commands/${1:-example_command}.md
   ```

3. **Edit the command file** with your desired prompt content:
   The file should contain the text you want Claude to process when the command is invoked.

4. **Optional: Add YAML frontmatter** for additional metadata:
   ```yaml
   ---
   title: ${1:-Example Command}
   description: ${3:-A helpful command for Claude Code}
   arguments: [arg1, arg2] # Optional arguments the command accepts
   ---
   ```

5. **Add argument support** with `$ARGUMENTS` or numbered variables:
   - Use `$ARGUMENTS` to access all arguments as a single string
   - Use `$1`, `$2`, etc. to access specific arguments
   - Use `${1:-default}` to provide default values

## Example Command Structure

Here's an example structure for your new `/${1:-example_command}` command:

```markdown
---
title: ${1:-Example Command}
description: ${3:-A helpful command for Claude Code}
arguments: [arg1, arg2]
---

# ${1:-Example Command}

This is the content of your command. When you invoke /${1:-example_command},
Claude will process this text as a prompt.

You can reference arguments:
- First argument: $1
- Second argument: $2
- All arguments: $ARGUMENTS

## Using This Command

Explain how to use this command effectively.
```

## Using Your New Command

Once created, you can invoke your command by typing:
`/${1:-example_command} [arguments]`

The command will be available:
- Project commands: Only in the specific project
- Personal commands: In all your Claude Code conversations

## Advanced Features

1. **File references**:
   ```
   Please analyze the code in @path/to/file.js
   ```

2. **Bash command execution**:
   ```
   Results of running a command:
   \`\`\`bash
   ls -la
   \`\`\`
   ```

3. **Command nesting**:
   You can invoke other commands from within a command.

## Command Template Based on Your Inputs

Here's a template for your new `/${1:-example_command}` command that incorporates your description:

```markdown
---
title: ${1:-Example Command}
description: ${3:-A helpful command for Claude Code}
arguments: [arg1, arg2]
---

# ${1:-Example Command}

${3:-A helpful command for Claude Code}

This command was created to help with specific tasks related to this purpose.

## Usage

How to use this command:
/${1:-example_command} [arguments]

## Implementation

The command will execute the following:

1. Step one
2. Step two
3. Step three

```

Would you like me to create this command file for you now? If so, please confirm the command name (`$1`), type (`$2`), and description (`$3`) I should use.
