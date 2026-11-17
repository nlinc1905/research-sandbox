"""Chat agent (LangChain/LangGraph) that calls the search agent via MCP.

Uses a fake chat model so no API keys are needed. It decides to call the
search tool only for some questions, so some chat traces have no search trace.
"""
import asyncio
import uuid
from typing import Any

import mlflow
from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_mcp_adapters.client import MultiServerMCPClient

from config import SEARCH_URL, setup_mlflow

setup_mlflow()
mlflow.langchain.autolog()  # traces the chat agent's LangGraph/LangChain calls

SEARCH_TRIGGERS = ("python", "mlflow", "mcp", "weather", "search", "look up")


def _text(content: Any) -> str:
    if isinstance(content, list):
        return " ".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    return str(content)


class FakeToolChatModel(BaseChatModel):
    """Deterministic stand-in for an LLM that supports tool calling."""

    @property
    def _llm_type(self) -> str:
        return "fake-tool-chat"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        last = messages[-1]
        if isinstance(last, ToolMessage):
            msg = AIMessage(content=f"Here's what I found: {_text(last.content)}")
        else:
            text = _text(last.content)
            if any(k in text.lower() for k in SEARCH_TRIGGERS):
                msg = AIMessage(
                    content="",
                    tool_calls=[{"name": "search_agent", "args": {"query": text},
                                 "id": f"call_{uuid.uuid4().hex[:8]}", "type": "tool_call"}],
                )
            else:
                msg = AIMessage(content=f"(no search needed) You said: {text}")
        return ChatResult(generations=[ChatGeneration(message=msg)])


QUESTIONS = [
    "Hi there, how are you?",
    "What is new in MLflow?",
    "Tell me a joke",
    "What is MCP?",
    "What's the weather like?",
    "Thanks, bye!",
]


async def main():
    client = MultiServerMCPClient(
        {"search": {"url": SEARCH_URL, "transport": "streamable_http"}}
    )
    tools = await client.get_tools()
    agent = create_agent(FakeToolChatModel(), tools)

    @mlflow.trace(name="chat_turn", span_type="AGENT")
    async def chat_turn(question: str) -> str:
        result = await agent.ainvoke({"messages": [{"role": "user", "content": question}]})
        return _text(result["messages"][-1].content)

    for q in QUESTIONS:
        print(f"\nUSER: {q}\nBOT:  {await chat_turn(q)}")


if __name__ == "__main__":
    asyncio.run(main())
