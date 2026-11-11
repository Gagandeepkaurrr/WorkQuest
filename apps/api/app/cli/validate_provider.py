"""Validate the built-in provider. No API keys, model calls or credits."""

import argparse

from app.ai.context import build_character_context
from app.ai.providers.local import LocalProvider
from app.ai.validation import validate_reply
from app.engine.registry import load_scenario
from app.engine.transitions import initial_state


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    scenario = load_scenario("checkout-outage")
    context = build_character_context(
        initial_state(scenario), scenario, "maya", [], "What should I inspect?"
    )
    for generate in (LocalProvider().character_reply, LocalProvider().debrief_coaching):
        result = generate(context)
        validate_reply(result.reply, context)
        assert result.input_tokens == result.output_tokens == 0
    print("PASS: built-in teammates and coaching; no model requests, no tokens, no API credits.")


if __name__ == "__main__":
    main()
