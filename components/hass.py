import logging
import time
from pydantic import BaseModel, AnyUrl, Field
from pygame import SRCALPHA, Font, Surface
import requests

class HassConfig(BaseModel):
    base_url: AnyUrl
    sensor_id: str = Field(..., min_length=1)
    api_key: str = Field(..., min_length=1)

class Hass(object):
    def __init__(self, cfg: HassConfig, font: Font):
        self.baseUrl = cfg.base_url
        self.sensorID = cfg.sensor_id
        self.headers = {"Authorization": "Bearer " + cfg.api_key, 'Content-Type': 'application/json'}
        self._temp = ""
        self._font = font
        self._last_update = 0.0

        self._update_freq = 180
        self.logger = logging.getLogger(__name__)

        self._update_temperature()

    @classmethod
    def block_height(cls):
        return 2

    def _update_temperature(self) -> None:
        self.logger.info("updating temperature")
        self._last_update = time.time()

        url = f"{self.baseUrl}/states/{self.sensorID}"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        data = resp.json()
        if "state" in data and "attributes" in data:
            if "unit_of_measurement" in data["attributes"]:
                t = float(data["state"])

                self._temp = str(round(t*10)/10) + "" + data["attributes"]["unit_of_measurement"]
                return

        self._temp = ""
        return

    def draw(self, width: int, height: int) -> Surface:
        if time.time() - self._last_update > self._update_freq:
            self._update_temperature()

        surface = Surface((width, height), SRCALPHA)
        text_surface = self._font.render(self._temp, True, (255, 255, 255))
        surface.blit(text_surface, (0, 0))
        return surface
