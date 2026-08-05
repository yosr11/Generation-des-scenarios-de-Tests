from pydantic import BaseModel, Field

from app.core.config import settings


class PipelineRequest(BaseModel):
    use_legacy_rag: bool = Field(default=True)
    model_agent1: str = Field(default="nova-lite-2")
    model_agent2: str = Field(default="nova-lite-2")
    model_agent3: str = Field(default="nova-lite-2")
    model_agent4_quality: str = Field(default="nova-lite-2")
    model_agent5: str = Field(default="nova-lite-2")


def test_pipeline_request_defaults_use_requested_models_and_legacy_rag():
    request = PipelineRequest()

    assert request.use_legacy_rag is True
    assert request.model_agent1 == "nova-lite-2"
    assert request.model_agent2 == "nova-lite-2"
    assert request.model_agent3 == "nova-lite-2"
    assert request.model_agent4_quality == "nova-lite-2"
    assert request.model_agent5 == "nova-lite-2"


def test_settings_defaults_match_requested_models():
    assert settings.AGENT1_DEFAULT_MODEL == "nova-lite-2"
    assert settings.AGENT3_DEFAULT_MODEL == "nova-lite-2"
    assert settings.AGENT4_QUALITY_MODEL == "nova-lite-2"
    assert settings.AGENT5_DEFAULT_MODEL == "nova-lite-2"
