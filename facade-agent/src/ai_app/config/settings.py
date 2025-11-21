from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE), env_file_encoding='utf-8', extra='ignore')

    default_model: str = Field(
        default="openai/gpt-4-turbo", env="default_model")
    aws_region: str = Field(default="us-west-2", env="AWS_REGION")
    default_max_tokens: int = Field(default=100, env="default_max_tokens")
    default_temperature: float = Field(default=0.7, env="default_temperature")
    mongo_url: str = Field(default="", env="mongo_url")
    mongo_db: str = Field(default="", env="mongo_db")
    postgres_url: str = Field(default="", env="postgres_url")


# For overriding different env file
# settings = AppSettings(_env_file='prod.env', _env_file_encoding='utf-8')
settings = AppSettings()
