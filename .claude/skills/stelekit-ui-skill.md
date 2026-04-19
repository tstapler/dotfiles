---
name: stelekit-ui-skill
description: Desktop UI automation for SteleKit Compose app. Launch app, take screenshots, click buttons, type text, verify UI state. Like playwright but for the SteleKit desktop app. Use when user wants to test SteleKit UI, debug visual issues, verify flows work, or automate desktop interaction.
---

**IMPORTANT - Path Resolution:**
This skill can be installed in different locations. Before executing any commands, determine the skill directory based on where you loaded this SKILL.md file, and use that path in all commands below. Replace `$SKILL_DIR` with the actual discovered path.

Common installation paths:

- Manual global: `~/.claude/skills/stelekit-ui-skill`
- Dotfiles: `~/dotfiles/.claude/skills/stelekit-ui-skill`
- Project-specific: `<project>/.claude/skills/stelekit-ui-skill`

# SteleKit Desktop UI Automation

General-purpose desktop automation for the SteleKit Compose Desktop app. Write Python scripts to launch the app, take screenshots, click, type, and verify UI state.

**CRITICAL WORKFLOW - Follow these steps in order:**

1. **Run setup if tools missing** - On first use or if xdotool/wmctrl/scrot are absent:

   ```bash
   python3 $SKILL_DIR/setup.py
   ```

2. **Write scripts to /tmp** - NEVER write scripts to the skill directory; always use `/tmp/stelekit-ui-*.py`

3. **Execute via run.py** - Always run scripts through the executor:

   ```bash
   python3 $SKILL_DIR/run.py /tmp/stelekit-ui-script.py
   ```

4. **Scripts import helpers** - Every script starts with `from helpers import *` (run.py adds `lib/` to sys.path automatically)

## How It Works

1. You describe what you want to test or automate
2. I write a Python script in `/tmp/stelekit-ui-*.py`
3. I execute it via: `python3 $SKILL_DIR/run.py /tmp/stelekit-ui-script.py`
4. Results printed to console; screenshots saved to `/tmp/`
5. I read screenshots with the Read tool to see what is on screen
6. I take follow-up screenshots to verify interactions worked

## Setup (First Time)

```bash
python3 $SKILL_DIR/setup.py
```

This installs `xdotool`, `wmctrl`, and `scrot` via pacman (Arch/Manjaro) or brew (macOS). Only needed once.

## Execution Pattern

**Step 1: Check if app is running and take initial screenshot**

```python
# /tmp/stelekit-ui-check.py
from helpers import *

wid = window_id()
if wid:
    print(f"SteleKit window found: {wid}")
    focus_stelekit()
else:
    print("SteleKit not running - launching...")
    launch_app()

path = screenshot('/tmp/stelekit-current.png')
print(f"Screenshot saved to {path}")
```

**Step 2: Execute from skill directory**

```bash
python3 $SKILL_DIR/run.py /tmp/stelekit-ui-check.py
```

**Step 3: Read the screenshot**

Use the Read tool to view `/tmp/stelekit-current.png` and see the current app state.

**Step 4: Interact based on what you see**

```python
# /tmp/stelekit-ui-interact.py
from helpers import *
focus_stelekit()
click_in_window(300, 400)       # click at (300, 400) relative to window top-left
type_text("My new page")
key("Return")
screenshot('/tmp/stelekit-after.png')
```

## Common Patterns

### Launch App and Screenshot

```python
# /tmp/stelekit-ui-launch.py
from helpers import *

if not window_id():
    launch_app(timeout=20)
else:
    focus_stelekit()

path = screenshot('/tmp/stelekit-home.png')
print(f"Screenshot: {path}")
```

### Click a Button by Approximate Location

```python
# /tmp/stelekit-ui-click.py
from helpers import *

focus_stelekit()
geo = window_geometry()
print(f"Window at x={geo[0]} y={geo[1]} w={geo[2]} h={geo[3]}")

# Take screenshot first to identify coordinates visually
screenshot('/tmp/stelekit-before-click.png')

# Click at a position within the window (relative coords)
click_in_window(x=150, y=80)
import time; time.sleep(0.5)

screenshot('/tmp/stelekit-after-click.png')
```

### Open Command Palette (Ctrl+K)

```python
# /tmp/stelekit-ui-cmd-palette.py
from helpers import *

focus_stelekit()
key("ctrl+k")
import time; time.sleep(0.3)
screenshot('/tmp/stelekit-cmd-palette.png')
```

### Search for a Page

```python
# /tmp/stelekit-ui-search.py
from helpers import *

focus_stelekit()
key("ctrl+k")              # open command palette
import time; time.sleep(0.3)
type_text("My Page Name")
time.sleep(0.3)
screenshot('/tmp/stelekit-search.png')
key("Return")              # confirm selection
time.sleep(0.5)
screenshot('/tmp/stelekit-navigated.png')
```

### Navigate to Journals

```python
# /tmp/stelekit-ui-journals.py
from helpers import *

focus_stelekit()
geo = window_geometry()
# Sidebar is on the left — Journals is typically near the top
# Take screenshot first to confirm layout
screenshot('/tmp/stelekit-sidebar.png')
```

### Type Into a Block Editor

```python
# /tmp/stelekit-ui-type.py
from helpers import *

focus_stelekit()
# Click on a block to focus it, then type
click_in_window(x=400, y=300)
import time; time.sleep(0.2)
type_text("Hello from automation")
time.sleep(0.2)
screenshot('/tmp/stelekit-typed.png')
```

## Inline Execution (Quick Tasks)

For simple one-off tasks, pass inline code as a string:

```bash
python3 $SKILL_DIR/run.py "
from helpers import *
focus_stelekit()
screenshot('/tmp/quick.png')
print('Done')
"
```

## Available Helpers

```python
from helpers import *

# Window management
wid = window_id()                     # Find SteleKit window ID (None if not running)
focus_stelekit()                      # Bring SteleKit to front
launch_app(wait=True, timeout=15)     # Launch if not running, wait for window
wait_for_window(timeout=15)           # Wait for window to appear, return ID
geo = window_geometry()               # Returns (x, y, width, height)

# Screenshots
path = screenshot('/tmp/out.png')     # Full screen screenshot
path = screenshot('/tmp/win.png', window='stelekit')  # Window screenshot

# Mouse & keyboard
click(x, y)                           # Click at absolute screen coordinates
click_in_window(x, y)                 # Click relative to SteleKit window top-left
type_text("hello world")              # Type text into focused window
key("ctrl+k")                         # Press key combo (xdotool keysym format)
key("Return")
key("Escape")
key("ctrl+shift+f")
```

## Tips

- **Always screenshot first** - Before clicking anything, take a screenshot and read it to understand the current UI state
- **Use relative coords** - `click_in_window(x, y)` is safer than `click(x, y)` since it offsets by window position
- **Wait after actions** - Use `import time; time.sleep(0.3)` after clicks/keystrokes before screenshotting
- **Check window exists** - Always call `window_id()` or `focus_stelekit()` before interacting
- **xdotool key syntax** - Use `ctrl+k`, `Return`, `Escape`, `Tab`, `ctrl+shift+p`, etc.

## Troubleshooting

**xdotool not found:**
```bash
python3 $SKILL_DIR/setup.py
```

**Window not found:**
- Make sure SteleKit is running: `python3 $SKILL_DIR/run.py "from helpers import *; launch_app()"`
- The window title pattern defaults to `stelekit` (case-insensitive)

**Screenshot is blank or wrong window:**
- Use `screenshot('/tmp/full.png')` for full screen instead of window-specific capture

**Click lands in wrong place:**
- Take a screenshot first, read it, identify coordinates visually, then click

## Example Usage

```
User: "Launch SteleKit and show me the current state"

Claude: I'll launch SteleKit and take a screenshot.
[Writes: /tmp/stelekit-ui-launch.py with launch_app() + screenshot()]
[Runs: python3 $SKILL_DIR/run.py /tmp/stelekit-ui-launch.py]
[Reads: /tmp/stelekit-home.png with the Read tool]
Here's what SteleKit looks like right now...
```

```
User: "Click the New Page button"

Claude: Let me first take a screenshot to find the button location.
[Takes screenshot, reads it]
I can see the New Page button at approximately (120, 45) in the window.
[Writes: click_in_window(120, 45) + screenshot to verify]
[Runs script, reads result screenshot]
Clicked successfully - new page dialog is now open.
```
