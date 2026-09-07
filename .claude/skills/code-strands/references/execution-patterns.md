# Execution Patterns: Streaming, Conversation Management, Instance Lifecycle

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

> For optimizing context windows, compaction, and sub-agent isolation, apply the `meta-context-engineering` skill.

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
