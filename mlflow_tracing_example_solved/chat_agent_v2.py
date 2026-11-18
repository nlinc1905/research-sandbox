"""Chat agent (LangChain/LangGraph) calling the search agent over MCP.

Each MCP tool call's remote trace is copied under that call's own LangChain
`tools` span. Any failure while merging falls back to returning the answer only.
"""
import asyncio
import json
import logging
import uuid
from typing import Any

import mlflow
from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from mlflow.langchain.langchain_tracer import MlflowLangchainTracer

from config import SEARCH_URL, setup_mlflow

log = logging.getLogger("trace_merge")
setup_mlflow()
mlflow.langchain.autolog()

ENVELOPE_KEY = "__mlflow_trace_envelope__"
KEYWORDS = ("python", "mlflow", "mcp", "weather")


def _text(content: Any) -> str:
    if isinstance(content, list):
        return " ".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    return str(content)


class FakeToolChatModel(BaseChatModel):
    """Deterministic stand-in for an LLM. One search call per keyword mentioned."""

    @property
    def _llm_type(self) -> str:
        return "fake-tool-chat"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        last = messages[-1]
        if isinstance(last, ToolMessage):
            results = []
            for m in reversed(messages):
                if not isinstance(m, ToolMessage):
                    break
                results.append(_text(m.content))
            msg = AIMessage(content="Here's what I found: " + " | ".join(reversed(results)))
        else:
            text = _text(last.content)
            hits = [k for k in KEYWORDS if k in text.lower()]
            if hits:
                calls = [{"name": "search_agent", "args": {"query": k},
                          "id": f"call_{uuid.uuid4().hex[:8]}", "type": "tool_call"} for k in hits]
                msg = AIMessage(content="", tool_calls=calls)
            else:
                msg = AIMessage(content=f"(no search needed) You said: {text}")
        return ChatResult(generations=[ChatGeneration(message=msg)])


def _langchain_tool_span(callbacks):
    """The LiveSpan MLflow's LangChain tracer opened for THIS tool call (or None).

    LangChain hands a tool coroutine a child callback manager if it declares a
    `callbacks` parameter; that manager's parent_run_id is the tool call's run id.
    Uses a private tracer method, so keep the fallback below if you upgrade MLflow.
    """
    try:
        # Iterate through the callback handlers to find the LangChain tracer.
        # Return the span corresponding to the tool call's run id if found.
        # The returned span is how the remote trace will be attached to the current chat trace.
        for handler in callbacks.handlers:
            if isinstance(handler, MlflowLangchainTracer):
                return handler._get_span_by_run_id(callbacks.parent_run_id)
    except Exception:
        pass
    return None


def _unpack(text: str):
    """Return (answer, trace_dict | None, original_trace_id | None). Never raises."""
    # Try to parse the text as a JSON envelope containing the answer and trace.
    try:
        data = json.loads(text)
        # If the data is a JSON envelope with the expected key, return the answer and trace.
        if isinstance(data, dict) and data.get(ENVELOPE_KEY):
            return data["answer"], data.get("trace"), data.get("original_trace_id")
    # Do not raise an exception if parsing fails; just return the plain text as the answer.
    except Exception:
        pass
    return text, None, None  # plain answer (older server, no trace, or malformed)


def _attach(trace, target, original_id):
    """Attach a remote trace to the target span, linking back to the original trace id if available."""
    mlflow.add_trace(trace, target=target)
    # If the original trace id is available, attach it as an attribute to the target span to link back to the standalone copy.
    if original_id:
        target.set_attribute("remote_trace_id", original_id)


def merge_remote_trace(mcp_tool):
    """Wrap an MCP tool: ask the server for its trace, copy it into the active chat trace."""
    async def _run(callbacks=None, **kwargs):
        """Invoke the remote MCP tool with trace merging."""
        # content = await mcp_tool.ainvoke({**kwargs, "include_trace": True})  # uncomment to go through LangChain
        content, _artifact = await mcp_tool.coroutine(**kwargs, include_trace=True)  # call the MCP tool's coroutine directly instead of going through LangChain
        # Try to unpack the raw response into answer, trace, and original trace id.
        answer, trace, original_id = _unpack(_text(content))
        if trace:
            # If a trace was successfully unpacked, attempt to attach it to the current span.
            try:
                # Get the current tool span from the LangChain callback manager.
                target = _langchain_tool_span(callbacks)
                if target is not None:
                    _attach(trace, target, original_id)
                # When the tool span is not found, hang the trace from a wrapper span instead
                else:
                    with mlflow.start_span(name=f"remote:{mcp_tool.name}") as wrapper:
                        _attach(trace, wrapper, original_id)
            except Exception as e:  # tracing must never break the chat
                log.warning("could not merge remote trace: %s", e)
        return answer

    # Construct the schema for the wrapped tool, excluding the `include_trace` argument.
    # The LLM never sees the `include_trace` argument; it is only used internally to fetch the trace from the remote tool.
    props = {k: v for k, v in mcp_tool.args_schema["properties"].items() if k != "include_trace"}
    return StructuredTool(
        name=mcp_tool.name,
        description=mcp_tool.description,
        args_schema={"type": "object", "properties": props, "required": ["query"]},
        coroutine=_run,
    )


QUESTIONS = [
    "Hi there, how are you?",
    "What is new in MLflow?",
    "Compare Python and MCP",          # two search calls in ONE chat turn
    "Tell me a joke",
    "What's the weather like?",
]


async def main():
    client = MultiServerMCPClient({"search": {"url": SEARCH_URL, "transport": "streamable_http"}})
    tools = [merge_remote_trace(t) for t in await client.get_tools()]
    agent = create_agent(FakeToolChatModel(), tools)

    @mlflow.trace(name="chat_turn", span_type="AGENT")
    async def chat_turn(question: str) -> str:
        # Invoke the agent with the user's question and merge any remote traces into the current chat turn.
        result = await agent.ainvoke({"messages": [{"role": "user", "content": question}]})
        # The result may contain a JSON envelope with the answer and trace.
        return _text(result["messages"][-1].content)

    for q in QUESTIONS:
        print(f"\nUSER: {q}\nBOT:  {await chat_turn(q)}")


if __name__ == "__main__":
    asyncio.run(main())
