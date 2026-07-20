from app.api.routes_orchestrator import PipelineRequest
from app.core.config import settings


def test_pipeline_request_defaults_use_requested_models_and_legacy_rag():
    request = PipelineRequest()

    assert request.use_legacy_rag is True
    assert request.model_agent1 == "nova-lite-2"
    assert request.model_agent15 == "nova-lite-2"
    assert request.model_agent2 == "nova-lite-2"
    assert request.model_agent3_quality == "nova-lite-2"
    assert request.model_agent5 == "nova-lite-2"


def test_settings_defaults_match_requested_models():
    assert settings.AGENT1_DEFAULT_MODEL == "nova-lite-2"
    assert settings.AGENT2_DEFAULT_MODEL == "nova-lite-2"
    assert settings.AGENT3_QUALITY_MODEL == "nova-lite-2"
    assert settings.AGENT5_DEFAULT_MODEL == "nova-lite-2"
