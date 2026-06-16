# ADR-002: Jinja2 with StrictUndefined
Status: Accepted
Date: 2026-06-15

## Context

cfgcaddy uses Jinja2 to render `.tmpl` source files before symlinking. Jinja2's `Environment` class controls how the template engine handles undefined variables.

The default Jinja2 `Environment()` uses `Undefined` behavior: when a template references a variable not present in the rendering context, the undefined reference silently renders as an empty string. For general web templating this is a reasonable default — a missing optional variable simply omits output. For dotfile rendering it is a critical defect:

- A shell script template containing `# Config for {{hostname}} machine` where `hostname` is not defined in `local.toml` will render as `# Config for  machine` with no error.
- A `.gitconfig` template with `email = {{ user_email }}` where `user_email` is missing renders as `email = ` — a syntactically valid but empty git email. Git silently uses the wrong identity.
- There is no indication that corruption occurred; `cfgcaddy link` exits 0.

Dotfiles are trusted configuration. Silent corruption is worse than a loud failure because the user may not discover the problem until much later, after the broken config has propagated to multiple machines or been committed.

Additionally, Jinja2's `{{ }}` delimiters conflict with some content in shell scripts and other config files. The most common problem is Go/Helm template syntax (`{{.Values.cluster}}`) and regex patterns using `{{[^}]*}}`. These raise `TemplateSyntaxError` at parse time with confusing messages like `unexpected char '^' at position 12`.

## Decision

Always instantiate the Jinja2 `Environment` with `undefined=StrictUndefined` and `autoescape=False`:

```python
from jinja2 import Environment, StrictUndefined

env = Environment(undefined=StrictUndefined, autoescape=False)
```

`StrictUndefined` raises `jinja2.UndefinedError` immediately when any undefined variable is accessed, with the variable name in the exception message.

`autoescape=False` is required because dotfiles are not HTML. HTML autoescaping would corrupt shell scripts by converting `<`, `>`, `&`, and `"` into HTML entities.

All `UndefinedError` and `TemplateSyntaxError` exceptions must be caught and re-raised with the template filename, line number, and an actionable hint:

```
ERROR: Template variable 'github_token' is undefined
  File: ~/dotfiles/.shell/secrets.sh.tmpl
  Hint: add 'github_token = "value"' to ~/.config/cfgcaddy/local.toml

ERROR: Template syntax error in ~/dotfiles/.shell/k8s.sh.tmpl at line 14
  Jinja2 message: unexpected char '.' at position 2
  Hint: if this file contains Go/Helm template syntax ({{.Values.*}}),
  wrap the affected block with {% raw %}...{% endraw %}
```

### Escape strategy for literal `{{` in shell scripts

Template authors who need a literal `{{` in their rendered output (e.g., a shell script that generates a Kubernetes manifest or calls a Go tool) have two options:

1. **Block escape** — wrap the section in `{% raw %}...{% endraw %}`:
   ```
   {% raw %}
   kubectl apply -f - <<EOF
   image: {{.Values.image}}
   EOF
   {% endraw %}
   ```

2. **Inline escape** — use `{{ '{{' }}` for a single literal `{{`:
   ```
   image: {{ '{{' }}.Values.image}}
   ```

This is the same approach chezmoi uses for its Go `text/template` engine, which has identical delimiter syntax.

## Alternatives Considered

**Default `Environment()` (Undefined behavior)**
Rejected. Silent empty-string substitution for missing variables is a data corruption risk for dotfiles. The user has no feedback that rendering produced incorrect output. This is the single highest-priority risk identified in the pitfalls research.

**`Environment(undefined=DebugUndefined)`**
Rejected. `DebugUndefined` renders missing variables as `{{ variable_name }}` — the original template syntax — rather than raising an error. This makes the rendered file look like it contains an unrendered template, which is confusing but not obviously broken. It also does not catch the error at render time; the user must inspect rendered output to detect the problem. `StrictUndefined` fails fast with a clear message.

**`Environment(undefined=ChainableUndefined)`**
Not applicable. `ChainableUndefined` allows attribute access on undefined values without raising. This makes the silent corruption problem worse, not better.

**Custom delimiters (e.g., `[[ var ]]` like chezmoi's option)**
Not adopted for the initial implementation. Custom delimiters eliminate conflicts with Go template syntax and shell `{{ }}` patterns, but they are a non-standard extension that increases template authoring friction and diverges from standard Jinja2. The `{% raw %}` escape mechanism handles the Go/Helm conflict adequately. Custom delimiters can be added as a future opt-in feature if user demand warrants it.

## Consequences

**Positive:**
- Missing variables raise immediately with the variable name — no silent corruption.
- Template authors receive actionable error messages pointing to the exact file and variable.
- `cfgcaddy link` exits non-zero when any template has an undefined variable, making failures detectable in scripts and CI.
- Consistent with how chezmoi and other mature dotfile template engines handle undefined variables.

**Negative:**
- Template authors who write shell scripts containing `{{ }}` syntax for other purposes (Go tools, Helm, regex patterns) will encounter `TemplateSyntaxError` at parse time. They must wrap those sections with `{% raw %}`.
- This is a breaking change for any existing `.tmpl` file that accidentally contains `{{ identifier }}` where the identifier is not a defined variable — those files relied on the silent empty-string behavior. (In practice, such files were silently broken before; `StrictUndefined` makes the breakage visible.)

**Test requirements:**
- Test that a template with an undefined variable raises `UndefinedError` and the error message contains the variable name.
- Test that the error message contains the template filename.
- Test that `autoescape=False` is in effect (verify `<` and `>` are not escaped in rendered output).
- Test the `{% raw %}` escape mechanism renders literal `{{` correctly.
