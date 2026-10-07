import app.config as config
from importlib import reload


def test_from_env_reads_project_dotenv(monkeypatch):
    for key in [
        "DEMO_MODE",
        "LLM_PROVIDER",
        "LLM_MODEL",
        "LLM_BASE_URL",
        "LLM_TIMEOUT_SECONDS",
        "OPENAI_API_KEY",
        "SERPER_API_KEY",
        "DATABASE_DIR",
        "LOG_LEVEL",
    ]:
        monkeypatch.delenv(key, raising=False)

    reload(config)
    settings = config.Settings.from_env()

    assert settings.openai_api_key == "ollama"
    assert settings.serper_api_key == "bce5047461f091c561fa6d4369f04f3cbd2d5732"
    assert settings.llm_timeout_seconds == 180.0
    assert settings.mode == "live"
