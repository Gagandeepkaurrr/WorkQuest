"""Official Google GenAI adapter; no tool execution, browsing or raw token streaming."""
from google import genai
from google.genai import types
from app.ai.contracts import CharacterContext,ProviderResult,Reply
from app.core.config import get_settings


class GeminiProvider:
    def __init__(self):
        self.settings=get_settings()
        self.client=genai.Client(api_key=self.settings.gemini_api_key.get_secret_value(),http_options=types.HttpOptions(timeout=self.settings.ai_timeout_seconds*1000,retry_options=types.HttpRetryOptions(attempts=1)))

    def _generate(self,context: CharacterContext,output_limit: int) -> ProviderResult:
        # generateContent remains supported by SDK 3.1; structured schema is supplied through the supported typed config.
        response=self.client.models.generate_content(model=self.settings.ai_model,contents=context.model_dump_json(),config=types.GenerateContentConfig(system_instruction=context.policy,response_mime_type='application/json',response_json_schema=Reply.model_json_schema(),max_output_tokens=output_limit))
        reply=Reply.model_validate_json(response.text or '')
        usage=response.usage_metadata
        return ProviderResult(reply=reply,provider='gemini',model=self.settings.ai_model,input_tokens=usage.prompt_token_count if usage else None,output_tokens=usage.candidates_token_count if usage else None)

    def character_reply(self,context: CharacterContext) -> ProviderResult:return self._generate(context,800)
    def debrief_coaching(self,context: CharacterContext) -> ProviderResult:return self._generate(context,1200)
