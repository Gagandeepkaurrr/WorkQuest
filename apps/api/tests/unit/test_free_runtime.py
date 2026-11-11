import socket
from types import SimpleNamespace
from uuid import uuid4

from app.ai.context import build_character_context
from app.ai.providers.local import LocalProvider
from app.ai.validation import validate_reply
from app.engine.registry import load_scenario
from app.engine.transitions import initial_state


def test_teammates_and_coaching_need_no_network_or_tokens(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Local replies must never open a network connection")

    monkeypatch.setattr(socket, "socket", forbidden)
    for slug in ("checkout-outage", "inventory-race", "analytics-timezone"):
        scenario = load_scenario(slug)
        context = build_character_context(
            initial_state(scenario), scenario, "maya", [], "What should I inspect?"
        )
        for method in (LocalProvider().character_reply, LocalProvider().debrief_coaching):
            result = method(context)
            validate_reply(result.reply, context)
            assert result.provider == "local"
            assert result.input_tokens == result.output_tokens == 0


def test_worker_cannot_select_a_remote_provider_from_old_metadata(monkeypatch):
    from app.jobs import tasks

    scenario = load_scenario("checkout-outage")
    context = build_character_context(
        initial_state(scenario), scenario, "maya", [], "What happened?"
    )
    lease = SimpleNamespace(
        job_id=uuid4(), token=uuid4(), provider="gemini", kind="dialogue", context=context
    )
    published = []

    def forbidden(*args, **kwargs):
        raise AssertionError("The free worker must not open a network connection")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(tasks, "claim_ai_job", lambda _: lease)
    monkeypatch.setattr(
        tasks, "publish_ai_result", lambda job_id, token, result: published.append(result)
    )
    tasks.execute_ai.run(str(lease.job_id))
    assert len(published) == 1
    assert published[0].provider == "local"
    assert published[0].input_tokens == published[0].output_tokens == 0
