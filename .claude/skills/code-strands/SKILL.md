---
name: code-strands
description: Best practices for the AWS Strands Agents SDK — structuring prompts, multi-agent patterns, structured I/O, and splitting monolithic agents into specialists. Use when designing or refactoring Strands-based agent systems.
---

# Strands Agents SDK Best Practices

## Core Philosophy

Strands is **model-driven**: agents decide what to do, tools define what's possible. Keep system prompts focused on a single domain of expertise. Fat prompts become brittle; specialists compose cleanly.

## `@tool` Decorator — How It Works

Strands builds the LLM tool spec from your function signature automatically:

```python
from strands import tool

@tool
def analyze_incident(incident_key: str, severity: str, days_back: int = 30) -> str:
    """Analyze a BTS incident and return classification recommendations.

    Args:
        incident_key: Jira ticket ID (e.g. BTS-12345)
        severity: P1, P2, P3, or P4
        days_back: Days back for comparison window
    """
    ...
```

- **First docstring paragraph** → tool description shown to the LLM (make it precise — this is the routing signal)
- **`Args:` section** → per-parameter descriptions in the tool spec
- **Type annotations** → JSON Schema types
- **Default values** → optional parameters

Override name/description or provide a full custom schema (e.g. for enums):

```python
@tool(name="get_weather", description="Retrieves weather forecast")
def weather_forecast(...): ...

@tool(inputSchema={"json": {"type": "object", "properties": {"shape": {"type": "string", "enum": ["circle", "rectangle"]}}, "required": ["shape"]}})
def calculate_area(shape: str): ...
```

## Agent-as-Tool Pattern (Primary Decomposition Strategy)

Wrap specialist agents in `@tool` functions. The orchestrator routes to them; each specialist has a short, focused system prompt.

```python
from strands import Agent, tool

@tool
def field_classification_specialist(context_json: str) -> str:
    """Assess missing classification fields and return a comment section if action needed."""
    agent = Agent(
        system_prompt=FIELD_CLASSIFICATION_PROMPT,  # ~60 lines, single concern
        tools=[get_transcript_field_suggestions, get_datadog_service_catalog, update_jira_field],
        callback_handler=None,  # suppress intermediate noise from appearing in orchestrator output
    )
    return str(agent(context_json))

# Orchestrator uses specialists as tools
orchestrator = Agent(
    system_prompt=ORCHESTRATOR_PROMPT,  # routing + combining logic only
    tools=[field_classification_specialist, mitigated_closure_specialist, coe_specialist],
)
```

**Key rules:**
- `callback_handler=None` on sub-agents — prevents duplicate/noisy output in the orchestrator's stream
- Each specialist gets only the tools it needs; don't share tool lists
- The `@tool` docstring IS the routing description — make it unambiguous

## Structured Outputs Between Agents

Use Pydantic models for typed inter-agent contracts instead of string blobs:

```python
from pydantic import BaseModel

class WorkflowResult(BaseModel):
    should_act: bool
    comment_section: str | None      # Markdown section for the combined comment
    auto_updates: list[FieldUpdate]  # Fields to apply before commenting
    flag_for_human: str | None       # Reason string if human review needed

# Agent produces structured output
result = agent("...", structured_output_model=WorkflowResult)
workflow_result: WorkflowResult = result.structured_output
```

**⚠ Known bug**: `structured_output_model` + `tools=` has known issues (GitHub #872, #891, #1032) where tool calls may not fire when structured output is active. A revamp is in progress. **Workaround**: use `structured_output_model` only on agents that don't need to call tools, or serialize the result as JSON string and deserialize on the receiving side.

**⚠ `str(AgentResult)` loses structured output**: when returning from an agent-as-tool, use `.model_dump_json()` to serialize the Pydantic model and parse it back on the orchestrator side:

```python
@tool
def my_specialist(query: str) -> str:
    agent = Agent(system_prompt=PROMPT, tools=[...], callback_handler=None)
    result = agent(query, structured_output_model=WorkflowResult)
    return result.structured_output.model_dump_json()  # serialize explicitly

# In orchestrator tool handler or post-processing:
workflow_result = WorkflowResult.model_validate_json(specialist_return_value)
```

## Passing Metadata Without Polluting LLM Context

Use `invocation_state` for configuration and metadata that tools need but the LLM shouldn't see in its token budget:

```python
result = orchestrator(message, invocation_state={
    "issue_key": "BTS-12345",
    "dry_run": True,
    "jira_base_url": "https://betfanatics.atlassian.net/browse",
})

# Tools access it via ToolContext — never visible in the LLM prompt
@tool(context=True)
def add_jira_comment(body: str, tool_context: ToolContext) -> str:
    issue_key = tool_context.invocation_state["issue_key"]
    dry_run = tool_context.invocation_state.get("dry_run", False)
    ...
```

**⚠ `invocation_state` does NOT auto-propagate to sub-agents**: when a `@tool` spawns a sub-agent, the parent's `invocation_state` is not forwarded automatically. You must thread it explicitly:

```python
@tool(context=True)
def my_specialist(query: str, tool_context: ToolContext) -> str:
    """Run specialist agent."""
    sub_agent = Agent(system_prompt=PROMPT, tools=[...], callback_handler=None)
    # Manually forward needed state into the prompt or invocation_state
    return str(sub_agent(query, invocation_state=tool_context.invocation_state))
```

## `Agent.__call__` Signature

```python
result: AgentResult = agent(
    prompt,                              # str | list[ContentBlock] | list[Message] | None
    invocation_state=None,               # dict — context for tools, invisible to LLM
    structured_output_model=None,        # per-call override of agent-level default
)

# AgentResult fields:
result.stop_reason          # why the agent stopped
result.message              # final message
result.metrics              # token counts, cycle durations, tool stats
result.structured_output    # populated if structured_output_model was set
```

**Note**: `prompt` must be `str`, `ContentBlock` list, `Message` list, or `None` — not a raw dict or dataclass. Structured context must be serialized into the string or passed via `invocation_state`.

## Multi-Agent Patterns (When to Use Each)

| Pattern | Use When | How Context Flows |
|---------|----------|-------------------|
| **Agent-as-Tool** | Orchestrator delegates to specialists; results combine | Orchestrator collects returns, aggregates |
| **Graph** | Conditional routing with LLM-decided paths, cycles OK | Full conversation transcript shared across nodes |
| **Swarm** | Agents hand off to peers; exploration/multidisciplinary | Shared context with prior agent knowledge |
| **Workflow (DAG)** | Repeatable pipeline, parallel steps, deterministic | Task-specific context from dependencies only |

For structured processes with one combined output (e.g. incident management): **Agent-as-Tool** is correct — specialists are called by an orchestrator that owns the final assembly.

## Monitoring Sub-Agent Tool Use (Async Streaming)

Bubble sub-agent events up through the tool layer using `stream_async`:

```python
@tool
async def my_specialist(query: str) -> AsyncIterator:
    """Run specialist agent and stream its progress."""
    agent = Agent(system_prompt=PROMPT, tools=[...], callback_handler=None)
    result = None
    async for event in agent.stream_async(query):
        yield event          # bubbles up tool_stream_event to parent callback
        if "result" in event:
            result = event["result"]
    yield str(result)
```

Graph/Swarm emit additional events: `multiagent_node_start`, `multiagent_node_stop`, `multiagent_handoff`, `multiagent_result`.

## Conversation Management (Context Window Control)

Three built-in strategies — pick based on session length and memory needs:

```python
from strands.agent.conversation_manager import (
    SlidingWindowConversationManager,
    SummarizingConversationManager,
)

# Default: drop oldest messages, truncate large tool results
agent = Agent(conversation_manager=SlidingWindowConversationManager(
    window_size=20,
    should_truncate_results=True,
    per_turn=True,   # proactive management before each model call
))

# Long-running agents that need early context: summarize instead of drop
agent = Agent(conversation_manager=SummarizingConversationManager(
    summary_ratio=0.3,
    preserve_recent_messages=10,
    summarization_agent=Agent(model=haiku_model),  # use a cheap model for summaries
))

# Manual control (no automatic truncation)
from strands.agent.conversation_manager import NullConversationManager
agent = Agent(conversation_manager=NullConversationManager())
```

For short-lived per-incident agents (our use case): `SlidingWindowConversationManager` with `per_turn=True` is appropriate — each agent run is bounded and fresh.

**Note**: Native token counting is not yet exposed (GitHub #1197); access `agent.messages` for manual inspection.

## Singleton vs Fresh Instance for Agent-as-Tool

```python
# Singleton: shared conversation history across all calls to this tool
_specialist = Agent(system_prompt="...", tools=[...])

@tool
def my_specialist(query: str) -> str:
    return str(_specialist(query))   # history accumulates — useful for stateful sessions


# Fresh instance: clean slate each call (our pattern for incident agents)
@tool
def my_specialist(query: str) -> str:
    agent = Agent(system_prompt="...", tools=[...], callback_handler=None)
    return str(agent(query))         # no cross-contamination between incidents
```

**For stateless, parallelized incident processing: always use fresh instances.**

## Prompt Sizing Guidelines

No SDK-imposed limit — the constraint is the model's context window. Practical guidance:
- **Orchestrator**: routing logic + cross-cutting rules only (~50-80 lines / ~200-400 tokens)
- **Specialist**: one workflow domain only (~40-80 lines / ~100-500 tokens)
- **Rule of thumb**: if a prompt has two `---` section separators for unrelated concerns, it should be two agents

## When to Split a Monolithic Agent

Split when **any** of these are true:
1. System prompt exceeds ~2,000 tokens with clearly distinct domain sections
2. Toolbelt has 15+ tools and wrong-tool selection is a recurring problem
3. Context window overflows regularly on complex runs
4. Some sub-tasks can run concurrently (use async)
5. Different domains warrant different model capabilities or costs
6. Multiple teams need to independently maintain different capabilities

**Model optimization** — the orchestrator only needs to route; use a cheap/fast model there. Specialist sub-agents can use more capable models where their domain requires it:

```python
orchestrator = Agent(
    model=BedrockModel(model_id="amazon.nova-lite-v1:0"),  # cheap router
    tools=[field_classification_specialist, mitigated_closure_specialist],
)
# Each specialist uses its own model (defaulting to Sonnet)
```

## Splitting a Monolithic Prompt

1. Identify independent "workflows" or "concerns" in the prompt
2. Each concern becomes a specialist with its own system prompt + minimal tool set
3. Cross-cutting rules (comment formatting, unassigned handling, section ordering) stay in the orchestrator
4. Define a `WorkflowResult` Pydantic model as the contract; serialize with `.model_dump_json()` across the agent-as-tool boundary
5. Add `context=True` to specialist `@tool` functions so they can forward `invocation_state`
6. Orchestrator collects results, applies auto-updates, assembles and posts one combined output

## Known Limitations (as of 2026-02)

| Issue | Impact | Workaround |
|-------|--------|------------|
| `structured_output_model` + `tools` conflicts (GH #872, #891, #1032) | Tool calls may not fire when structured output active | Separate output-producing agents from tool-calling agents; serialize via JSON string |
| `invocation_state` not auto-propagated to sub-agents | Sub-agent tools can't see parent state | Pass `tool_context.invocation_state` explicitly to sub-agent `invocation_state=` |
| `str(AgentResult)` drops `structured_output` | Pydantic models lost across agent-as-tool boundary | Use `.model_dump_json()` / `model_validate_json()` explicitly |
| Structured output is Python-only | No TypeScript structured output | N/A |

## Reference

- [Agents as Tools](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/agents-as-tools/)
- [Multi-Agent Patterns](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/multi-agent-patterns/)
- [Structured Output](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/agents/structured-output/)
- [Custom Tools](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/tools/custom-tools/)
- [Callback Handlers / Streaming](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/streaming/callback-handlers/)
- [Agent API Reference](https://strandsagents.com/latest/documentation/docs/api-reference/python/agent/agent/)
- [strands-agents/samples](https://github.com/strands-agents/samples)
- [Deep Agents pattern (community)](https://www.pierreange.ai/blog/deep-agents-using-strands)
