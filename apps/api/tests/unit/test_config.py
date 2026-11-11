import pytest

from app.core.config import Settings


def test_production_rejects_local_defaults():
    with pytest.raises(ValueError):
        Settings(app_env="production", app_origin="http://localhost:5173", demo_enabled=True)


@pytest.mark.parametrize("provider", ["gemini", "openai", "anthropic"])
def test_paid_providers_are_rejected_even_with_credentials(provider):
    with pytest.raises(ValueError):
        Settings(ai_provider=provider, gemini_api_key="credential-present", ai_model="any-model")


def test_local_provider_is_the_only_runtime_and_legacy_mock_is_compatible(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    assert Settings(_env_file=None).ai_provider == "local"
    assert Settings(ai_provider="local").ai_provider == "local"


@pytest.mark.parametrize("scheme", ["postgresql", "postgres"])
def test_render_database_url_uses_psycopg(scheme):
    config = Settings(
        database_url=f"{scheme}://user:password@private-host:5432/workquest",
        backend_hostname="workquest-api.onrender.com",
    )
    assert (
        config.database_url.get_secret_value()
        == "postgresql+psycopg://user:password@private-host:5432/workquest"
    )
    assert config.backend_hostname == "workquest-api.onrender.com"


@pytest.mark.parametrize("hostname", ["*", "https://api.example.com", "api.example.com:8000"])
def test_backend_hostname_is_exact(hostname):
    with pytest.raises(ValueError):
        Settings(backend_hostname=hostname)
