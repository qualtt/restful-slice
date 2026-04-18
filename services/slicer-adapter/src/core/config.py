from functools import lru_cache
from typing import Optional
from urllib.parse import quote

from pydantic import AliasChoices, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    rabbitmq_url: Optional[str] = Field(default=None, validation_alias="RABBITMQ_URL")
    rabbitmq_user: str = Field(default="guest", validation_alias="RABBITMQ_USER")
    rabbitmq_password: str = Field(
        default="guest", validation_alias="RABBITMQ_PASSWORD"
    )
    rabbitmq_host: str = Field(default="rabbitmq", validation_alias="RABBITMQ_HOST")
    rabbitmq_port: int = Field(default=5672, validation_alias="RABBITMQ_PORT")

    minio_endpoint: str = Field(validation_alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(
        validation_alias=AliasChoices("MINIO_ACCESS_KEY", "MINIO_ROOT_USER")
    )
    minio_secret_key: str = Field(
        validation_alias=AliasChoices("MINIO_SECRET_KEY", "MINIO_ROOT_PASSWORD")
    )
    minio_bucket: str = Field(
        validation_alias=AliasChoices("MINIO_BUCKET", "MINIO_BUCKET_NAME")
    )
    minio_secure: bool = Field(default=False, validation_alias="MINIO_SECURE")

    orca_api_url: str = Field(
        default="http://slicer_api:3000",
        validation_alias=AliasChoices("ORCA_API_URL", "SLICER_API_URL"),
    )

    event_spec_version: str = Field(
        default="1.0.0", validation_alias="EVENT_SPEC_VERSION"
    )
    service_name: str = Field(default="slicer-adapter", validation_alias="SERVICE_NAME")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def amqp_url(self) -> str:
        if self.rabbitmq_url:
            return self.rabbitmq_url
        user = quote(self.rabbitmq_user, safe="")
        password = quote(self.rabbitmq_password, safe="")
        return f"amqp://{user}:{password}@{self.rabbitmq_host}:{self.rabbitmq_port}/"


@lru_cache
def get_settings() -> Settings:
    return Settings()
