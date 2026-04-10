from pydantic import BaseModel
import yaml


class Settings(BaseModel):
    policy: str
    max_bytes: int
    default_ttl: int
    origin_base_url: str
    request_timeout: int = 10


def load_settings(path: str = "config.yml") -> Settings:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Settings(**data)