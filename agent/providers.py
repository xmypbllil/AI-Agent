"""Provider-backed LLM adapters for the agent layer."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from agent.llm import LLMAdapter, LocalMvpAdapter
from runtime.actions import Action, ActionGraph, OpenApplicationAction, RunCommandAction


Transport = Callable[[str, Mapping[str, str], Mapping[str, Any]], Mapping[str, Any]]


SYSTEM_PROMPT = """You are a planning adapter for Desktop LLM Runtime.
Return only JSON with this shape:
{"actions":[{"type":"run_command","command":"...","cwd":"."}]}

Allowed action types:
- run_command: execute a shell command through the existing Runtime.
- open_application: launch an application through the existing Runtime.

Do not invent new actions. Prefer validation commands that already exist in the project.
"""


def urllib_transport(url: str, headers: Mapping[str, str], payload: Mapping[str, Any]) -> Mapping[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=dict(headers),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM provider returned HTTP {exc.code}: {body}") from exc


@dataclass(slots=True)
class OpenAICompatibleAdapter(LLMAdapter):
    """OpenAI-compatible HTTP adapter implemented without importing an SDK."""

    api_key: str
    model: str = "gpt-4.1-mini"
    base_url: str = "https://api.openai.com/v1/chat/completions"
    transport: Transport = urllib_transport
    last_prompt: Mapping[str, Any] = field(default_factory=dict)
    last_plan: Mapping[str, Any] = field(default_factory=dict)

    def generate_plan(self, goal: str, context: Mapping[str, Any]) -> ActionGraph:
        prompt = self._prompt(goal, context)
        self.last_prompt = prompt
        response = self.transport(
            self.base_url,
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            prompt,
        )
        plan = self._extract_plan(response)
        self.last_plan = plan
        return action_graph_from_plan(plan)

    def decide_next_action(
        self,
        goal: str,
        observations: Mapping[str, Any],
        previous_actions: tuple[Any, ...],
        reason: str,
    ) -> ActionGraph | None:
        if not observations.get("errors"):
            return None
        return self.generate_plan(goal, observations)

    def _prompt(self, goal: str, context: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "goal": goal,
                            "context": dict(context),
                            "suggested_validation": [
                                "python -m compileall agent computer runtime tests evaluations",
                                "python -m evaluations.run_validation",
                            ],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }

    def _extract_plan(self, response: Mapping[str, Any]) -> Mapping[str, Any]:
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("LLM response does not contain choices")
        message = choices[0].get("message")
        if not isinstance(message, Mapping):
            raise ValueError("LLM response choice does not contain a message")
        content = message.get("content")
        if not isinstance(content, str):
            raise ValueError("LLM response message does not contain JSON content")
        parsed = json.loads(content)
        if not isinstance(parsed, Mapping):
            raise ValueError("LLM plan JSON must be an object")
        return parsed


def action_graph_from_plan(plan: Mapping[str, Any]) -> ActionGraph:
    raw_actions = plan.get("actions")
    if not isinstance(raw_actions, list):
        raise ValueError("LLM plan must contain an actions list")
    actions: list[Action] = []
    for raw_action in raw_actions:
        if not isinstance(raw_action, Mapping):
            raise ValueError("Each LLM action must be an object")
        action_type = raw_action.get("type")
        if action_type == "run_command":
            command = raw_action.get("command")
            if not isinstance(command, str) or not command:
                raise ValueError("run_command action requires a command")
            cwd = raw_action.get("cwd")
            timeout = float(raw_action.get("timeout_seconds", 240.0))
            actions.append(
                RunCommandAction(command, cwd=str(cwd) if cwd else ".", timeout_seconds=timeout)
            )
        elif action_type == "open_application":
            target = raw_action.get("target")
            if not isinstance(target, str) or not target:
                raise ValueError("open_application action requires a target")
            timeout = float(raw_action.get("timeout_seconds", 30.0))
            actions.append(
                OpenApplicationAction(target, timeout_seconds=timeout)
            )
        else:
            raise ValueError(f"Unsupported LLM action type: {action_type!r}")
    return ActionGraph(actions=tuple(actions))


def create_adapter_from_env() -> LLMAdapter:
    provider = os.environ.get("LLM_PROVIDER", "local").strip().lower()
    if provider in {"", "local", "none"}:
        return LocalMvpAdapter()
    api_key = os.environ.get("API_KEY")
    if not api_key:
        raise RuntimeError("API_KEY is required when LLM_PROVIDER is not local")
    if provider in {"openai", "openai-compatible"}:
        return OpenAICompatibleAdapter(
            api_key=api_key,
            model=os.environ.get("LLM_MODEL", "gpt-4.1-mini"),
            base_url=os.environ.get(
                "LLM_BASE_URL",
                "https://api.openai.com/v1/chat/completions",
            ),
        )
    raise RuntimeError(f"Unsupported LLM_PROVIDER: {provider}")
