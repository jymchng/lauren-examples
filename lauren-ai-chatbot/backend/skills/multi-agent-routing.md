# Multi-Agent Routing

## Contents
- Agent roster and roles
- HandoffTo typed routing tool
- ActiveAgentStore — tracks active agent per conversation
- Per-agent conversation isolation
- Controller routing loop
- CheckAuthModule shared tool pattern

## Agent roster

| Agent class | Name constant | Role |
|---|---|---|
| `UnauthenticatedCRMAgent` | `UNAUTH_CRM_AGENT_NAME` | Public, pre-login questions; routes via `HandoffToAuthenticatedCRM` |
| `AuthenticatedCRMAgent` | `AUTH_CRM_AGENT_NAME` | Balances, history, general banking; hands off to Transfer or Disputes |
| `BankTransferAgent` | `TRANSFER_AGENT_NAME` | Fund transfer specialist; HITL approval gate |
| `DisputesAgent` | `DISPUTES_AGENT_NAME` | Disputes, fraud, chargebacks |

Routing graph:

```
Public CRM ──(auth)──► Auth CRM ◄──► Transfer ◄──► Disputes
```

Each agent gets its own `InMemoryConversationStore` and only sees turns it handled directly. Context crosses handoff boundaries via a summary string, not the full history.

## HandoffTo typed routing

`HandoffTo[AgentA, AgentB]` generates a subclass whose `to_agent` parameter is
`Literal["<AgentA name>", "<AgentB name>"]`. The LLM can only produce valid agent
names — misspellings are caught at JSON-schema validation time before any tool runs.

```python
# In AgentModule.for_root() — register the generated HandoffTo subclass as a tool
_AuthCRMModule = AgentModule.for_root(
    agents=[AuthenticatedCRMAgent],
    tools=[HandoffTo[BankTransferAgent, DisputesAgent]],
    ...
)
```

`HandoffTo.run()` does three things:
1. Sets `ActiveAgentStore.set(conversation_id, to_agent)`
2. Stores a handoff summary via `ActiveAgentStore.set_pending_summary()`
3. Emits an `agent_handoff` WebSocket event so the frontend can update its indicator

The controller detects the store change and loops to the new agent on the next iteration.

If the active agent is already `to_agent`, `HandoffTo` still refreshes the store
and pending summary but suppresses the duplicate `agent_handoff` WebSocket event.
This keeps the activity feed free of repeated no-op handoff rows.

## ActiveAgentStore

```python
# app/ai/tools/active_agent_store.py
@injectable(scope=Scope.SINGLETON)
class ActiveAgentStore:
    def get(self, conversation_id: str, default: str) -> str: ...
    def set(self, conversation_id: str, agent_name: str) -> None: ...
    def set_pending_summary(self, conversation_id: str, summary: str) -> None: ...
    def pop_pending_summary(self, conversation_id: str) -> str | None: ...
```

`pop_pending_summary` returns the summary **once** and clears it. The controller
prepends it to the next agent's prompt so the receiving agent has context without
seeing the full prior-agent history.

## Per-agent conversation isolation

Each agent declares its **own** `InMemoryConversationStore()` on `@agent(conversation_store=...)`.
A shared store causes agents to re-read prior handoff summaries as instructions and
trigger wrong `HandoffTo` calls. Per-agent stores keep contexts isolated.

```python
@agent(
    name=AUTH_CRM_AGENT_NAME,
    model=None,
    system=_SYSTEM,
    max_turns=8,
    conversation_store=InMemoryConversationStore(),   # isolated — not shared
)
@use_tools(GetBalanceTool, HandoffTo, CheckAuthenticationTool)
class AuthenticatedCRMAgent: ...
```

The `conversation_id` passed to `runner.run_stream()` is namespaced per agent:
`f"{conv_id}:{active_agent_name}"` so stores never collide.

## Controller routing loop

```python
active = active_agent_store.get(conv_id, default_agent)
prompt = full_prompt
handoffs = 0
max_handoffs = 8

while True:
    agent, runner = _resolve_agent(active)

    async for chunk in await runner.run_stream(
        agent, prompt,
        conversation_id=f"{conv_id}:{active}",
        execution_context=exec_ctx,
        metadata={"conversation_id": conv_id},
    ):
        if chunk.delta:
            yield ServerSentEvent(event="token", data=chunk.delta)

    new_active = active_agent_store.get(conv_id, default_agent)
    if new_active == active or handoffs >= max_handoffs:
        break

    handoffs += 1
    summary = active_agent_store.pop_pending_summary(conv_id)
    yield ServerSentEvent(event="break", data=new_active)

    if summary:
        prompt = (
            auth_prefix
            + f"[HANDOFF from {active}]: {summary}\n\n"
            + f"[ORIGINAL REQUEST]: {raw_message}"
        )
    else:
        prompt = full_prompt
    active = new_active

yield ServerSentEvent(event="done", data="")
```

The `break` SSE event tells the frontend to display a separator and update the
active-agent indicator before the next agent starts streaming.

## CheckAuthModule shared tool pattern

`CheckAuthenticationTool` is needed by all four agents. It lives in `CheckAuthModule`,
which each `AgentModule` imports. Listing it in `shared_tools=` prevents
`ModuleExportViolation` (re-registering an already-exported provider):

```python
_AuthCRMModule = AgentModule.for_root(
    agents=[AuthenticatedCRMAgent],
    imports=[LLMProvider, CheckAuthModule, BankingModule, WsModule, ActiveAgentModule],
    shared_tools=[CheckAuthenticationTool, GetBalanceTool, GetTransactionHistoryTool],
    signals=signal_bus,
)
```

`shared_tools=` tells the framework to borrow the already-registered singleton
rather than attempt a second registration. Apply the same pattern for any tool
imported by more than one `AgentModule`.
