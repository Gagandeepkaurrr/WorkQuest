import pytest
from app.core.config import Settings

def test_production_rejects_local_defaults():
    with pytest.raises(ValueError):
        Settings(app_env='production', app_origin='http://localhost:5173', demo_enabled=True)

def test_live_provider_requires_model_and_key():
    with pytest.raises(ValueError):
        Settings(ai_provider='gemini', gemini_api_key='', ai_model='')
