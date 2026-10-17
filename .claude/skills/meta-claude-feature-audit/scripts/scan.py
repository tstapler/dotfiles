"""Compare a skills tree to the current Claude Code docs.

Usage: python3 -I scan.py <skills_dir> <docs_dir>

Valid frontmatter keys and built-in command names are parsed from the docs
(skills.md, commands.md), not hardcoded, so the report tracks the docs.
"""
import collections
import pathlib
import re
import sys

skills_dir, docs_dir = map(pathlib.Path, sys.argv[1:3])

for name in ("skills.md", "commands.md"):
    if not (docs_dir / name).is_file():
        sys.exit(f"scan.py: {docs_dir / name} not found; run fetch-docs.sh first")
skills_doc = (docs_dir / "skills.md").read_text()
START, END = "### Frontmatter reference", "#### Using skill frontmatter"
if START not in skills_doc or END not in skills_doc.split(START, 1)[-1]:
    sys.exit(f"scan.py: skills.md is missing the '{START}' / '{END}' markers; docs layout changed, update scan.py")
fm_section = skills_doc.split(START, 1)[1].split(END, 1)[0]
valid_keys = set(re.findall(r"^\| `([a-z_-]+)` \|", fm_section, re.M))
commands = sorted(set(re.findall(r"^\| `/([a-z][a-z-]*)", (docs_dir / "commands.md").read_text(), re.M)))
if not valid_keys or not commands:
    sys.exit(f"scan.py: parsed {len(valid_keys)} frontmatter keys and {len(commands)} commands; docs table format changed, update scan.py")
LOOP_RE = re.compile(r"(?i)max (iterations|rounds)|loop until|until (green|clean|passing)|repeat until|poll(ing)? (every|until)")

used = collections.Counter()
invalid = collections.defaultdict(list)
no_desc, cmd_refs, loops = [], collections.defaultdict(list), []

for f in sorted(skills_dir.rglob("SKILL.md")):
    rel = str(f.relative_to(skills_dir))
    text = f.read_text(errors="ignore")
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    keys = set(re.findall(r"^([A-Za-z_][\w-]*):", m.group(1), re.M)) if m else set()
    for k in keys:
        used[k] += 1
        if k not in valid_keys:
            invalid[k].append(rel)
    if "description" not in keys:
        no_desc.append(rel)
    body = text[m.end():] if m else text
    for c in commands:
        if re.search(rf"(?<![\w:/-])/{re.escape(c)}(?![\w-])", body):
            cmd_refs[c].append(rel)
    if LOOP_RE.search(body):
        loops.append(rel)

print(f"## Skills: {sum(1 for _ in skills_dir.rglob('SKILL.md'))}  valid frontmatter keys per docs: {len(valid_keys)}")
print("\n## Documented keys never used:", ", ".join(sorted(valid_keys - set(used))) or "none")
print("\n## Keys not in docs (silently ignored by Claude Code):")
for k, fs in sorted(invalid.items(), key=lambda kv: -len(kv[1])):
    print(f"- {k} ({len(fs)}): {', '.join(fs[:6])}{' ...' if len(fs) > 6 else ''}")
print(f"\n## No description ({len(no_desc)}):", ", ".join(no_desc))
print("\n## Built-in commands referenced by skills (count):")
print(", ".join(f"/{c}={len(cmd_refs[c])}" for c in commands if cmd_refs[c]))
print("\n## Built-ins never referenced:", ", ".join(f"/{c}" for c in commands if not cmd_refs[c]))
print(f"\n## Hand-rolled loop/iteration language ({len(loops)}) - /goal or Stop-hook candidates:")
print("\n".join(f"- {p}  {'(already mentions /goal)' if p in cmd_refs['goal'] else ''}" for p in loops))
