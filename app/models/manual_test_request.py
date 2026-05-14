from pydantic import BaseModel


class ManualTestGenerationRequest(BaseModel):
    story_id: str
