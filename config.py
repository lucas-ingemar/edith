from pydantic import BaseModel, AnyUrl, Field, ValidationError
from typing import List
import toml
import os

from components import ImmichConfig, HassConfig, VasttrafikConfig


class GeneralConfig(BaseModel):
    blur: bool

class Config(BaseModel):
    general: GeneralConfig
    immich: ImmichConfig
    hass: HassConfig
    vasttrafik: VasttrafikConfig


def get_config(config_filename: str) -> Config:
    # Load toml
    config_data = toml.load(config_filename)

    # Override with environment variables if present
    config_data["immich"]["api_key"] = os.getenv("EDITH_IMMICH_API_KEY", "")
    config_data["hass"]["api_key"] = os.getenv("EDITH_HASS_API_KEY", "")
    config_data["vasttrafik"]["client_key"] = os.getenv("EDITH_VT_CLIENT_KEY", "")
    config_data["vasttrafik"]["client_secret"] = os.getenv("EDITH_VT_SECRET_KEY", "")

    return Config(**config_data)
