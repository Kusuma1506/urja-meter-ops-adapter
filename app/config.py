import os
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, field_validator

load_dotenv()


class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    URJA_BASE_URL: str = Field(default="https://urja-ops.flockenergy.tech")
    URJA_USERNAME: str | None = Field(default=None)
    URJA_PASSWORD: str | None = Field(default=None)
    REQUEST_TIMEOUT: float = Field(default=10.0)
    LOG_LEVEL: str = Field(default="INFO")

    @field_validator("REQUEST_TIMEOUT")
    @classmethod
    def validate_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("REQUEST_TIMEOUT must be greater than zero")
        return value


def get_settings() -> Settings:
    payload: dict[str, Any] = {
        "URJA_BASE_URL": os.getenv("URJA_BASE_URL", "https://urja-ops.flockenergy.tech"),
        "URJA_USERNAME": os.getenv("URJA_USERNAME"),
        "URJA_PASSWORD": os.getenv("URJA_PASSWORD"),
        "REQUEST_TIMEOUT": float(os.getenv("REQUEST_TIMEOUT", "10")),
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
    }
    return Settings(**payload)
