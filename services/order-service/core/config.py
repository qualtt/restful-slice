from functools import lru_cache
from urllib.parse import quote

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Явный alias нужен для env: иначе в ряде версий pydantic-settings не матчится
    # RABBITMQ_USER / RABBITMQ_PASSWORD из Docker, берутся дефолты guest/guest
    # (на брокере тогда видно PLAIN refused: user 'guest').
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", populate_by_name=True
    )

    rabbitmq_url: str | None = Field(default=None, alias="RABBITMQ_URL")
    rabbitmq_user: str = Field(default="guest", alias="RABBITMQ_USER")
    rabbitmq_password: str = Field(default="guest", alias="RABBITMQ_PASSWORD")
    rabbitmq_host: str = Field(default="rabbitmq", alias="RABBITMQ_HOST")
    rabbitmq_port: int = Field(default=5672, alias="RABBITMQ_PORT")

    minio_endpoint: str = Field(default="minio:9000", validation_alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(
        default="minioadmin",
        validation_alias=AliasChoices("MINIO_ACCESS_KEY", "MINIO_ROOT_USER"),
    )
    minio_secret_key: str = Field(
        default="minio_secret_123",
        validation_alias=AliasChoices("MINIO_SECRET_KEY", "MINIO_ROOT_PASSWORD"),
    )
    minio_bucket: str = Field(
        default="3d-models",
        validation_alias=AliasChoices("MINIO_BUCKET", "MINIO_BUCKET_NAME"),
    )
    minio_secure: bool = Field(default=False, validation_alias="MINIO_SECURE")

    inventory_url: str = Field(
        default="http://inventory_service:8081",
        validation_alias="INVENTORY_URL",
    )

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
