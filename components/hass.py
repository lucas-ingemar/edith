import logging
from pathlib import Path
import time
from pydantic import BaseModel, AnyUrl, Field
from pygame import SRCALPHA, Font, Surface
from pygame.font import SysFont
import requests

BASE_DIR = str(Path(__file__).resolve().parent.parent)

_icon_map = {
"clear-night": "󰖔",
"cloudy": "󰖐",
"fog": "󰖑",
"hail": "󰖒",
"lightning": "󰖓",
"lightning-rainy": "󰙾",
"partlycloudy": "󰖕",
"pouring": "󰖖",
"rainy": "󰖗",
"snowy": "󰖘",
"snowy-rainy": "󰙿",
"sunny": "󰖙",
"windy": "󰖝",
"windy-variant": "󰖞",
"exceptional": "󰼸",
"unavailable": "󰨹",
}

class HassConfig(BaseModel):
    base_url: AnyUrl
    temp_sensor_id: str = Field(..., min_length=1)
    smhi_sensor_id: str = Field(..., min_length=1)
    api_key: str = Field(..., min_length=1)

class Hass(object):
    def __init__(self, cfg: HassConfig):
        self.baseUrl = cfg.base_url
        self.cfg = cfg
        self.headers = {"Authorization": "Bearer " + cfg.api_key, 'Content-Type': 'application/json'}
        self._temp = ""
        self._temp_unit = ""
        self._weather_state = ""
        self._wind = ""
        self._wind_gust = ""
        self._wind_unit= ""
        self._last_update = 0.0

        self._temp_font = SysFont("DejaVu Sans", 25)
        self._wind_font = SysFont("DejaVu Sans", 20)
        self._wind_gust_font = SysFont("DejaVu Sans", 16)
        self._nerd_font = Font(BASE_DIR + "/fonts/SymbolsNerdFontMono-Regular.ttf", 50)
        self._update_freq = 180
        self.logger = logging.getLogger(__name__)

    @classmethod
    def block_count(cls):
        return 2

    def _update_temperature(self) -> None:
        self.logger.info("updating temperature")

        url = f"{self.baseUrl}/states/{self.cfg.temp_sensor_id}"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        data = resp.json()
        if "state" in data and "attributes" in data:
            if "unit_of_measurement" in data["attributes"]:
                t = float(data["state"])

                self._temp = str(round(t*10)/10)
                self._temp_unit = data["attributes"]["unit_of_measurement"]
                return

        self._temp = ""
        return

    def _update_smhi(self) -> None:
        self.logger.info("updating smhi")

        url = f"{self.baseUrl}/states/{self.cfg.smhi_sensor_id}"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        data = resp.json()
        if "state" in data and "attributes" in data:
            self._weather_state = data["state"]
            if all(key in data["attributes"] for key in ["wind_speed", "wind_gust_speed", "wind_speed_unit"]):
                da = data["attributes"]
                self._wind = "%.1f" % da["wind_speed"]
                self._wind_gust = "%.1f" % da["wind_gust_speed"]
                self._wind_unit = da["wind_speed_unit"]

                return

        return

    def _update_surface(self, width: int, height: int):
        self._surface = Surface((width, height), SRCALPHA)

        icon_surface = self._nerd_font.render(_icon_map[self._weather_state], True, (255,255,255))
        temp_surface = self._temp_font.render(self._temp, True, (255, 255, 255))
        temp_unit_surface = self._wind_font.render(self._temp_unit, True, (255, 255, 255))
        wind_surface = self._wind_font.render(self._wind, True, (255, 255, 255))
        wind_unit_surface= self._wind_gust_font.render(self._wind_unit, True, (255, 255, 255))

        self._surface.blit(icon_surface, (0, 0))
        self._surface.blit(temp_surface, (icon_surface.get_width() + 5, 5))
        self._surface.blit(temp_unit_surface, (icon_surface.get_width() + temp_surface.get_width() + 7, 6))
        self._surface.blit(wind_surface, (icon_surface.get_width() + 5, 5 + temp_surface.get_height()))
        self._surface.blit(wind_unit_surface, (icon_surface.get_width() + wind_surface.get_width() + 9, 5 + temp_surface.get_height()))

    def draw(self, width: int, height: int) -> Surface:
        if time.time() - self._last_update > self._update_freq:
            self._update_temperature()
            self._update_smhi()
            self._last_update = time.time()

        return self._surface
