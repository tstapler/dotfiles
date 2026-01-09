# Handy Plan Handler

**Purpose**: Process [[Needs Handy Plan]] tags by creating comprehensive construction/repair project plans with tools, parts, safety guidelines, and step-by-step instructions.

**Status**: Production-ready handler for knowledge enrichment orchestrator

**Integration**: Works as part of knowledge enrichment pipeline

---

## Handler Interface

### Input Parameters

```yaml
entry_content: string      # Full journal entry text
journal_date: string       # YYYY-MM-DD format
line_number: int          # Line number in journal file
file_path: string         # Absolute path to journal file
repo_path: string         # Repository root path
```

### Output Format

```yaml
status: "success|partial|failed"
pages_created:
  - "[[Project Name]]"
pages_updated: []
issues: []
metadata:
  project: string
  difficulty: "easy|medium|hard|expert"
  estimated_time: string
  cost_range: string
  tools_required: int
  steps: int
```

---

## Processing Methodology

### Phase 1: Extract Project Details

Identify what needs a handy plan:

```python
def extract_project_details(entry_content: str) -> dict:
    """
    Extract project details from entry.

    Patterns:
    1. Direct mention: "Fix [[711 N 60th Front Door]] [[Needs Handy Plan]]"
    2. Action-based: "Need to repair X [[Needs Handy Plan]]"
    3. Problem statement: "X is broken [[Needs Handy Plan]]"
    """
    # Extract primary subject
    match = re.search(r'\[\[(.+?)\]\].*?\[\[Needs Handy Plan\]\]', entry_content)
    if match:
        subject = match.group(1)
        return {
            'subject': subject,
            'action': extract_action(entry_content),
            'problem': extract_problem_description(entry_content),
            'context': entry_content
        }

    return {'subject': None}


def extract_action(content: str) -> str:
    """Extract the action verb (fix, install, replace, repair, etc.)."""
    actions = ['fix', 'repair', 'replace', 'install', 'build', 'renovate',
               'restore', 'upgrade', 'modify', 'adjust']

    for action in actions:
        if action in content.lower():
            return action

    return 'work on'


def extract_problem_description(content: str) -> str:
    """Extract description of the problem from context."""
    # Look for descriptive text before or after the tag
    # E.g., "slipping thumb turn" or "needs new paint"
    sentences = content.split('.')
    for sentence in sentences:
        if '[[Needs Handy Plan]]' in sentence:
            # Clean up and return relevant part
            return sentence.replace('[[Needs Handy Plan]]', '').strip()

    return ''
```

### Phase 2: Research Project Requirements

Gather information about similar projects:

```python
def research_project(subject: str, action: str, problem: str) -> dict:
    """
    Research project requirements, tools, materials, and process.

    Returns: {
        overview: str,
        difficulty: str,
        estimated_time: str,
        tools: list[str],
        materials: list[dict],  # {item, quantity, estimated_cost}
        steps: list[str],
        safety_notes: list[str],
        tips: list[str],
        cost_range: str
    }
    """
    # Build search query
    query = f"how to {action} {subject} {problem} DIY guide"

    # Perform web search
    search_results = perform_web_search(query, max_results=10)

    # Analyze results
    analysis = analyze_handy_guides(search_results)

    return {
        'overview': analysis['summary'],
        'difficulty': analyze_difficulty(analysis),
        'estimated_time': estimate_time(analysis),
        'tools': extract_tools(analysis),
        'materials': extract_materials(analysis),
        'steps': extract_steps(analysis),
        'safety_notes': extract_safety_notes(analysis),
        'tips': extract_tips(analysis),
        'cost_range': estimate_cost(analysis)
    }


def analyze_difficulty(analysis: dict) -> str:
    """
    Determine difficulty level: easy|medium|hard|expert

    Factors:
    - Number of specialized tools required
    - Technical skill needed
    - Physical demands
    - Safety risks
    - Time investment
    """
    indicators = analysis.get('difficulty_indicators', [])

    expert_keywords = ['licensed', 'professional', 'permit required', 'structural']
    hard_keywords = ['complex', 'precision', 'multiple days', 'expensive tools']
    medium_keywords = ['moderate', 'common tools', 'weekend project']

    content = ' '.join(indicators).lower()

    if any(keyword in content for keyword in expert_keywords):
        return 'expert'
    elif any(keyword in content for keyword in hard_keywords):
        return 'hard'
    elif any(keyword in content for keyword in medium_keywords):
        return 'medium'
    else:
        return 'easy'


def extract_tools(analysis: dict) -> list[str]:
    """
    Extract required tools from research.

    Categories:
    - Hand tools
    - Power tools
    - Measuring tools
    - Safety equipment
    - Specialized tools
    """
    # Common tools and their categories
    tools = []

    # Extract from search results
    for result in analysis.get('sources', []):
        # Parse tool lists from content
        tool_matches = re.findall(
            r'(?:tools|equipment|supplies):?\s*([^\.]+)',
            result.get('content', ''),
            re.IGNORECASE
        )
        for match in tool_matches:
            # Split by commas or bullets
            items = re.split(r'[,\n•\-]', match)
            tools.extend([item.strip() for item in items if item.strip()])

    # Deduplicate and categorize
    return sorted(list(set(tools)))


def extract_materials(analysis: dict) -> list[dict]:
    """
    Extract materials/parts needed with quantities and costs.

    Returns: [
        {item: "Wood screws", quantity: "1 box", cost: "$5-10"},
        {item: "Sandpaper", quantity: "assorted grits", cost: "$5"},
    ]
    """
    materials = []

    # Parse materials sections from research
    for result in analysis.get('sources', []):
        material_sections = re.findall(
            r'(?:materials|parts|supplies):?\s*([^\.]+)',
            result.get('content', ''),
            re.IGNORECASE
        )

        for section in material_sections:
            # Parse individual items
            items = re.split(r'[,\n•\-]', section)
            for item in items:
                if item.strip():
                    materials.append({
                        'item': item.strip(),
                        'quantity': 'as needed',
                        'cost': 'varies'
                    })

    return materials
```

### Phase 3: Create Project Plan

Generate comprehensive handy plan page:

```python
def create_handy_plan_page(
    subject: str,
    action: str,
    research_data: dict,
    repo_path: str
) -> dict:
    """
    Create Logseq page with complete handy plan.

    Page structure:
    - tags:: [[Home Improvement]], [[Project Type]]
    - difficulty:: [easy|medium|hard|expert]
    - estimated_time:: X hours/days
    - cost_range:: $X - $Y

    # Project Name

    ## Overview
    [What needs to be done and why]

    ## Difficulty
    - Rating: [difficulty]
    - Estimated Time: [time]
    - Cost Range: [range]

    ## Tools Required
    ### Hand Tools
    - Tool 1
    - Tool 2

    ### Power Tools
    - Tool 1
    - Tool 2

    ### Safety Equipment
    - Item 1
    - Item 2

    ## Materials & Parts
    | Item | Quantity | Estimated Cost |
    |------|----------|---------------|
    | ... | ... | ... |

    ## Safety Considerations
    - Safety note 1
    - Safety note 2

    ## Step-by-Step Instructions
    ### Phase 1: Preparation (X min)
    1. Step 1
    2. Step 2

    ### Phase 2: Main Work (X hours)
    1. Step 1
    2. Step 2

    ### Phase 3: Finishing (X min)
    1. Step 1
    2. Step 2

    ## Tips & Best Practices
    - Tip 1
    - Tip 2

    ## When to Call a Professional
    - Scenario 1
    - Scenario 2

    ## Sources
    - [Source 1](url)
    - [Source 2](url)

    ## Related Projects
    - [[Related Project 1]]
    - [[Related Project 2]]
    """
    page_content = generate_handy_plan_content(
        subject, action, research_data
    )

    # Determine page title
    page_title = f"{subject}" if '60th' in subject else f"{action.title()} {subject}"

    # Write to pages directory
    page_path = Path(repo_path) / 'logseq' / 'pages' / f'{page_title}.md'

    try:
        page_path.parent.mkdir(parents=True, exist_ok=True)
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(page_content)

        return {
            'success': True,
            'page_created': f'[[{page_title}]]',
            'word_count': len(page_content.split())
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def generate_handy_plan_content(
    subject: str,
    action: str,
    research_data: dict
) -> str:
    """Generate formatted handy plan page."""
    # Build page title
    title = f"{subject}" if '60th' in subject else f"{action.title()} {subject}"

    content = f"""tags:: [[Home Improvement]], [[Handy Plan]]
difficulty:: {research_data['difficulty']}
estimated_time:: {research_data['estimated_time']}
cost_range:: {research_data['cost_range']}
category:: Project Plan

# {title}

## Overview

{research_data['overview']}

## Difficulty

- **Rating**: {research_data['difficulty'].title()}
- **Estimated Time**: {research_data['estimated_time']}
- **Cost Range**: {research_data['cost_range']}

## Tools Required

{format_tools(research_data['tools'])}

## Materials & Parts

{format_materials_table(research_data['materials'])}

## Safety Considerations

{format_list(research_data['safety_notes'])}

## Step-by-Step Instructions

{format_steps(research_data['steps'])}

## Tips & Best Practices

{format_list(research_data['tips'])}

## When to Call a Professional

{generate_professional_scenarios(research_data['difficulty'])}

## Related Topics

- [[Home Improvement]]
- [[{subject}]]
"""

    return content


def format_tools(tools: list[str]) -> str:
    """Format tools into categorized lists."""
    # Categorize tools
    hand_tools = []
    power_tools = []
    safety = []

    power_keywords = ['drill', 'saw', 'sander', 'grinder', 'router']
    safety_keywords = ['goggles', 'gloves', 'mask', 'helmet', 'ear']

    for tool in tools:
        tool_lower = tool.lower()
        if any(kw in tool_lower for kw in power_keywords):
            power_tools.append(tool)
        elif any(kw in tool_lower for kw in safety_keywords):
            safety.append(tool)
        else:
            hand_tools.append(tool)

    output = ""
    if hand_tools:
        output += "### Hand Tools\n" + '\n'.join(f'- {t}' for t in hand_tools) + "\n\n"
    if power_tools:
        output += "### Power Tools\n" + '\n'.join(f'- {t}' for t in power_tools) + "\n\n"
    if safety:
        output += "### Safety Equipment\n" + '\n'.join(f'- {t}' for t in safety) + "\n\n"

    return output


def format_materials_table(materials: list[dict]) -> str:
    """Format materials as markdown table."""
    if not materials:
        return "No specific materials required.\n"

    table = "| Item | Quantity | Estimated Cost |\n"
    table += "|------|----------|----------------|\n"

    for material in materials:
        table += f"| {material['item']} | {material['quantity']} | {material['cost']} |\n"

    return table + "\n"


def format_steps(steps: list[str]) -> str:
    """Format steps with phases."""
    if not steps:
        return "1. Follow manufacturer instructions\n"

    # Group steps into phases
    phases = group_steps_into_phases(steps)

    output = ""
    for phase_name, phase_steps in phases.items():
        output += f"\n### {phase_name}\n\n"
        for i, step in enumerate(phase_steps, 1):
            output += f"{i}. {step}\n"

    return output


def group_steps_into_phases(steps: list[str]) -> dict:
    """Group steps into logical phases."""
    # Simple grouping: prep, main, finish
    num_steps = len(steps)
    prep_count = max(1, num_steps // 4)
    finish_count = max(1, num_steps // 4)

    return {
        'Phase 1: Preparation': steps[:prep_count],
        'Phase 2: Main Work': steps[prep_count:-finish_count],
        'Phase 3: Finishing': steps[-finish_count:]
    }
```

### Phase 4: Update Journal

Mark plan as created:

```python
def mark_plan_complete(
    file_path: str,
    line_number: int,
    project: str
) -> dict:
    """
    Replace [[Needs Handy Plan]] with completion marker.
    Format: ~~[[Needs Handy Plan]]~~ ✓ Created comprehensive repair plan
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if 0 <= line_number < len(lines):
            line = lines[line_number]
            updated_line = line.replace(
                '[[Needs Handy Plan]]',
                f'~~[[Needs Handy Plan]]~~ ✓ Created comprehensive repair plan'
            )
            lines[line_number] = updated_line

        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return {'success': True}

    except Exception as e:
        return {'success': False, 'error': str(e)}
```

---

## Complete Handler Implementation

```python
#!/usr/bin/env python3
"""
Handy Plan Handler

Process [[Needs Handy Plan]] tags by creating comprehensive project plans.
"""

import re
from pathlib import Path
from typing import Any


def handle_handy_plan_request(
    entry_content: str,
    journal_date: str,
    line_number: int,
    file_path: str,
    repo_path: str
) -> dict[str, Any]:
    """
    Main handler for [[Needs Handy Plan]] tags.

    Returns:
        {
            status: "success|partial|failed",
            pages_created: list[str],
            pages_updated: list[str],
            issues: list[str],
            metadata: dict
        }
    """
    issues = []

    # Phase 1: Extract project details
    project_info = extract_project_details(entry_content)

    if not project_info.get('subject'):
        return {
            'status': 'failed',
            'pages_created': [],
            'pages_updated': [],
            'issues': ['Could not determine project subject'],
            'metadata': {}
        }

    subject = project_info['subject']
    action = project_info.get('action', 'work on')
    problem = project_info.get('problem', '')

    # Phase 2: Research project
    research_data = research_project(subject, action, problem)

    if not research_data['overview']:
        return {
            'status': 'failed',
            'pages_created': [],
            'pages_updated': [],
            'issues': ['Research failed to gather information'],
            'metadata': {}
        }

    # Phase 3: Create plan page
    page_result = create_handy_plan_page(subject, action, research_data, repo_path)

    if not page_result['success']:
        return {
            'status': 'failed',
            'pages_created': [],
            'pages_updated': [],
            'issues': [page_result.get('error', 'Page creation failed')],
            'metadata': {}
        }

    # Phase 4: Mark complete
    mark_result = mark_plan_complete(file_path, line_number, subject)
    if not mark_result['success']:
        issues.append(f"Failed to update journal: {mark_result.get('error')}")

    return {
        'status': 'success' if not issues else 'partial',
        'pages_created': [page_result['page_created']],
        'pages_updated': [],
        'issues': issues,
        'metadata': {
            'project': subject,
            'difficulty': research_data['difficulty'],
            'estimated_time': research_data['estimated_time'],
            'cost_range': research_data['cost_range'],
            'tools_required': len(research_data['tools']),
            'steps': len(research_data['steps'])
        }
    }


# Implementation functions from above...
```

---

## Example Plans

### Easy Project
```
Title: Replace Light Switch
Difficulty: Easy
Time: 30 minutes
Cost: $5-15
Tools: Screwdriver, wire tester
Steps: 5
```

### Medium Project
```
Title: Install Ceiling Fan
Difficulty: Medium
Time: 2-3 hours
Cost: $50-200
Tools: Drill, wire stripper, ladder
Steps: 12
```

### Hard Project
```
Title: 711 N 60th Front Door Lock Repair
Difficulty: Hard
Time: 2-4 hours
Cost: $20-100
Tools: Full toolkit, penetrating oil, specialized tools
Steps: 15+
```

---

## Integration with Orchestrator

```python
if '[[Needs Handy Plan]]' in entry_content:
    result = handle_handy_plan_request(
        entry_content=entry_content,
        journal_date=journal_date,
        line_number=line_number,
        file_path=file_path,
        repo_path=repo_path
    )

    if result['status'] == 'success':
        log_success(f"Created plan: {result['metadata']['project']}")
        log_info(f"Difficulty: {result['metadata']['difficulty']}")
        log_info(f"Time: {result['metadata']['estimated_time']}")
    else:
        log_error(f"Plan creation failed: {result['issues']}")
```

---

## Safety Emphasis

All plans include:
1. **Safety equipment requirements**
2. **Risk warnings** for dangerous steps
3. **When to call a professional** guidance
4. **Building codes** and permit considerations

---

## Testing

```python
TEST_CASES = [
    {
        'entry': '- Fix [[711 N 60th Front Door]] lock [[Needs Handy Plan]]',
        'expected_difficulty': 'hard',
        'should_include_safety': True
    },
    {
        'entry': '- Need to replace light bulb [[Needs Handy Plan]]',
        'expected_difficulty': 'easy',
        'estimated_time': '< 30 min'
    }
]
```
