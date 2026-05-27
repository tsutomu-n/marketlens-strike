from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    data_dir: Path = Path("data")
    log_level: str = "INFO"
    fred_api_key: str | None = Field(default=None, validation_alias="FRED_API_KEY")
    default_timeframes: str = "4h,1d,3d"

    model_config = SettingsConfigDict(env_prefix="SIS_", env_file=".env", extra="ignore")

    @property
    def default_timeframe_list(self) -> list[str]:
        return [item.strip() for item in self.default_timeframes.split(",") if item.strip()]


def get_settings() -> Settings:
    return Settings()
