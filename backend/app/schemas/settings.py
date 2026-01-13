from typing import Optional
from pydantic import BaseModel, Field


class PlatformSettingsBase(BaseModel):
    jenkins_url: Optional[str] = Field(None, description="Base URL of Jenkins instance")
    jenkins_username: Optional[str] = Field(None, description="Jenkins username")
    jenkins_api_token: Optional[str] = Field(None, description="Jenkins API token")

    ai_provider: Optional[str] = Field("openai", description="AI provider identifier")
    ai_base_url: Optional[str] = Field(None, description="Custom AI base URL")
    ai_api_key: Optional[str] = Field(None, description="AI provider API key")
    ai_model: Optional[str] = Field(None, description="Preferred AI model")

    artifact_storage_path: Optional[str] = Field("/var/lib/mtp/artifacts", description="Artifact storage root")
    notification_email: Optional[str] = Field(None, description="Notification recipient email")


class PlatformSettingsResponse(PlatformSettingsBase):
    id: int

    class Config:
        orm_mode = True


class UpdatePlatformSettings(PlatformSettingsBase):
    pass
