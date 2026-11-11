import pytest

from app.core.config import Settings


def test_production_rejects_local_defaults():
    with pytest.raises(ValueError):
        Settings(app_env="production", app_origin="http://localhost:5173", demo_enabled=True)


def test_live_provider_requires_model_and_key():
    with pytest.raises(ValueError):
        Settings(ai_provider="gemini", gemini_api_key="", ai_model="")


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
