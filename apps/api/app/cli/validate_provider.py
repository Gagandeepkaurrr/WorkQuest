"""Explicit live smoke probe: one bounded generation, potentially billable."""

import argparse

from app.ai.contracts import CharacterContext
from app.ai.providers.gemini import GeminiProvider
from app.ai.validation import validate_reply
from app.core.config import get_settings

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--live", action="store_true", help="Authorize one real provider request")
args = parser.parse_args()
if not args.live or get_settings().ai_provider != "gemini":
    parser.error("Requires --live and AI_PROVIDER=gemini. Mock tests do not verify credentials.")
context = CharacterContext(
    teammate_id="maya",
    name="Maya",
    role="Probe",
    persona="State that no evidence is available.",
    briefing="Integration verification",
    fallback="No evidence available.",
    facts=[],
    allowed_action_ids=[],
    transcript=[],
    message="Is evidence available?",
)
try:
    result = GeminiProvider().character_reply(context)
    validate_reply(result.reply, context)
except Exception as exc:
    print(f"NOT VERIFIED: {type(exc).__name__}. Inspect credentials/model/network privately.")
    raise SystemExit(1)
print(
    f"PASS: structured response from {result.provider}/{result.model}; input_tokens={result.input_tokens}, output_tokens={result.output_tokens}. No raw response retained."
)
