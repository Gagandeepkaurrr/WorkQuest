import re

from app.ai.contracts import CharacterContext, Reply


def validate_reply(reply: Reply, context: CharacterContext) -> Reply:
    if set(reply.referenced_fact_ids) - {f.id for f in context.facts}:
        raise ValueError("Disallowed fact reference")
    if set(reply.suggested_action_ids) - set(context.allowed_action_ids):
        raise ValueError("Disallowed action reference")
    if re.search(r"<[^>]*>|https?://|!\[", reply.reply_text, re.I):
        raise ValueError("Unsafe response markup")
    return reply
