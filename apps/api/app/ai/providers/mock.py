from app.ai.contracts import CharacterContext,ProviderResult,Reply


class MockProvider:
    def __init__(self,failure: str | None=None):self.failure=failure

    def character_reply(self,context: CharacterContext) -> ProviderResult:
        if self.failure=='timeout':raise TimeoutError('Injected provider timeout')
        if self.failure=='invalid':return ProviderResult(reply=Reply(reply_text='Invalid reference',referenced_fact_ids=['not-allowed']),provider='mock',model='authored-v1')
        text=context.message.lower()
        if any(word in text for word in ('execute','run the action','set_flag','deploy now')):
            reply=Reply(reply_text='I can discuss the evidence, but I cannot execute an operation. Use Actions to review a simulated change yourself.')
        elif any(word in text for word in ('ignore','hidden','reveal the fix','system prompt')):
            reply=Reply(reply_text=context.fallback)
        else:
            facts=[f for f in context.facts if f.artifact_id]
            match=next((f for f in facts if any(word in f.text.lower() for word in text.split() if len(word)>4)),facts[-1] if facts else None)
            reply=Reply(reply_text=f'From the evidence you opened: {match.text} What would you verify next?' if match else context.fallback,referenced_fact_ids=[match.id] if match else [])
        return ProviderResult(reply=reply,provider='mock',model='authored-v1',input_tokens=0,output_tokens=0)

    def debrief_coaching(self,context: CharacterContext) -> ProviderResult:
        return ProviderResult(reply=Reply(reply_text='Compare the checks you completed with the missed checks in your assessment. Try a saved checkpoint and change one decision, then verify its effect. The score above is calculated by the simulation.'),provider='mock',model='authored-v1',input_tokens=0,output_tokens=0)
