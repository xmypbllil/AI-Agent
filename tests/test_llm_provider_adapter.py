from typing import Any, Mapping

from agent.providers import OpenAICompatibleAdapter, action_graph_from_plan
from runtime.actions.models import ActionKind


def test_action_graph_from_llm_plan_uses_existing_actions() -> None:
    graph = action_graph_from_plan(
        {
            "actions": [
                {"type": "run_command", "command": "python -m compileall agent", "cwd": "."},
                {"type": "open_application", "target": "notepad.exe"},
            ]
        }
    )

    actions = graph.ordered()
    assert [action.kind for action in actions] == [
        ActionKind.RUN_COMMAND,
        ActionKind.OPEN_APPLICATION,
    ]


def test_openai_compatible_adapter_generates_plan_with_fake_transport() -> None:
    captured: dict[str, Any] = {}

    def fake_transport(
        url: str,
        headers: Mapping[str, str],
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = payload
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"actions":[{"type":"run_command",'
                            '"command":"python -m compileall agent","cwd":"."}]}'
                        )
                    }
                }
            ]
        }

    adapter = OpenAICompatibleAdapter(api_key="test-key", transport=fake_transport)

    graph = adapter.generate_plan("check project", {})

    actions = graph.ordered()
    assert len(actions) == 1
    assert actions[0].kind is ActionKind.RUN_COMMAND
    assert actions[0].inputs["command"] == "python -m compileall agent"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert adapter.last_prompt
    assert adapter.last_plan
