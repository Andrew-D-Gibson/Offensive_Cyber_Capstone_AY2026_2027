"""
llm_client.py

A minimal, swappable interface so the agent harness doesn't care whether
it's talking to a local Ollama model, the Anthropic API, or a scripted
fake for testing the harness mechanics with zero model calls.

Start with MockScriptedLLM to shake out bugs in the agent loop / parsing
logic before spending any real inference. Swap in OllamaClient or
AnthropicClient once the harness works end-to-end.
"""

from abc import ABC, abstractmethod
from typing import List, Dict


class LLMClient(ABC):
    @abstractmethod
    def complete(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """messages: [{"role": "system"|"user"|"assistant", "content": str}, ...]
        Returns the raw text completion."""
        raise NotImplementedError


class MockScriptedLLM(LLMClient):
    """Replays a fixed list of responses in order. Useful for unit-testing
    the agent loop / parser without burning real inference calls. Raises
    once the script runs out, so you notice if the harness needs more steps
    than expected."""

    def __init__(self, script: List[str]):
        self.script = list(script)
        self._i = 0

    def complete(self, messages, **kwargs) -> str:
        if self._i >= len(self.script):
            raise RuntimeError("MockScriptedLLM: script exhausted — agent needed more steps than scripted")
        resp = self.script[self._i]
        self._i += 1
        return resp


class OllamaClient(LLMClient):
    """Talks to a local Ollama server. Requires `requests`.
    Example: OllamaClient(model="qwen2.5:14b")"""

    def __init__(self, model: str, host: str = "http://localhost:11434"):
        self.model = model
        self.host = host

    def complete(self, messages, **kwargs) -> str:
        import requests
        resp = requests.post(
            f"{self.host}/api/chat",
            json={"model": self.model, "messages": messages, "stream": False, **kwargs},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]


class AnthropicClient(LLMClient):
    """Talks to the Anthropic API. Requires `pip install anthropic` and
    ANTHROPIC_API_KEY set in the environment."""

    def __init__(self, model: str = "claude-sonnet-4-6", max_tokens: int = 1024):
        import anthropic
        self.client = anthropic.Anthropic()
        self.model = model
        self.max_tokens = max_tokens

    def complete(self, messages, **kwargs) -> str:
        # Anthropic separates system prompt from the message list.
        system = ""
        chat_messages = []
        for m in messages:
            if m["role"] == "system":
                system += m["content"] + "\n"
            else:
                chat_messages.append(m)
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system.strip(),
            messages=chat_messages,
            **kwargs,
        )
        return "".join(block.text for block in resp.content if block.type == "text")
