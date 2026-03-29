import base64
from datetime import UTC, datetime, timezone
import json
import logging
from typing import List
from dateutil import parser
from pydantic import BaseModel, Field
from pygame import SRCALPHA, Font, Surface, draw as pygdraw
import requests
import time as timelib

TOKEN_URL = "https://ext-api.vasttrafik.se/token"
API_BASE_URL = "https://ext-api.vasttrafik.se/pr/v4"
CONSUMER_KEY = "<YOUR_CONSUMER_KEY>"
CONSUMER_SECRET = "<YOUR_CONSUMER_SECRET>"


class VasttrafikConfig(BaseModel):
    stop: str = Field(..., min_length=1)
    platform: str = Field(..., min_length=1)
    lines: List[int]
    client_key: str = Field(..., min_length=1)
    client_secret: str = Field(..., min_length=1)


class Vasttrafik(object):
    def __init__(self, font: Font, cfg: VasttrafikConfig):
        self.font = font
        self.cfg = cfg
        self.client = Client("json", key=cfg.client_key, secret=cfg.client_secret)
        self.data = []
        self._departures = []
        self._updated_at = 0
        self._update_freq = 5 * 60
        self.logger = logging.getLogger(__name__)

    @classmethod
    def block_count(cls) -> int:
        return 4

    def _sort_departures(self, deps):
        def time_difference(entry):
            # Parse the time string to datetime
            entry_time = parser.isoparse(entry["estimatedOtherwisePlannedTime"])
            # Get the current time in UTC
            now = datetime.now(UTC).replace(tzinfo=entry_time.tzinfo)
            # Calculate the absolute difference between the times
            return abs((entry_time - now).total_seconds())

        return sorted(deps, key=time_difference)

    def _filter_past_departures(self, deps):
        filtered_deps = []
        for d in deps:
            dt = datetime.fromisoformat(d["estimatedOtherwisePlannedTime"])
            # Get current time with timezone
            now = datetime.now(timezone.utc)
            # Convert dt to UTC for fair comparison
            dt_utc = dt.astimezone(timezone.utc)
            if dt_utc > now:
                filtered_deps.append(d)

        return filtered_deps

    # def _all_departures_exists(self) -> bool:
    #     for line in self.cfg.lines:
    #         count = 0
    #         for d in self._departures:
    #             if int(d["serviceJourney"]["line"]["shortName"]) == line:
    #                 count += 1
    #         if count < 2:
    #             return False

    #     return True

    def _time_diff(self, time_string):
        target_time = datetime.fromisoformat(time_string)
        current_time = datetime.now(target_time.tzinfo)  # Ensure timezone is matched
        time_difference = target_time - current_time
        minutes_difference = round(time_difference.total_seconds() / 60)
        formatted_time_difference = f"{minutes_difference} m"
        return formatted_time_difference

    def _update_departures(self):
        self.logger.info("updating departure data")
        self._updated_at = timelib.time()

        s = self.client.get_stop_by_name(self.cfg.stop)
        if s is None:
            self.logger.error("could not get information about the stop")
            return

        deps = []

        d = self.client.get_departures(s["gid"], self.cfg.platform)
        for dd in d:
            if dd["serviceJourney"]["line"]["shortName"] in [str(l) for l in self.cfg.lines]:
                deps.append(dd)

        if len(deps) > 0:
            deps = self._sort_departures(deps)

        self._departures = deps

    def _update_data(self):
        self.logger.debug("updating formatted data")

        if timelib.time() - self._updated_at > self._update_freq:
            self._update_departures()


        self._departures = self._filter_past_departures(self._departures)

        # if not self._all_departures_exists():
        #     self._update_departures()


        deps = self._departures.copy()
        vtdata = list()

        if len(deps) > 0:
            deps = self._sort_departures(deps)


        lines = self.cfg.lines.copy()
        for idx in range(len(deps)):
            if len(lines) == 0:
                break

            d = deps[idx]

            line = int(d["serviceJourney"]["line"]["shortName"])

            if line not in lines:
                continue

            time = self._time_diff(d["estimatedOtherwisePlannedTime"])
            if time == "0 m" or time.startswith("-"):
                time = "nu"

            ld = {
                "line": str(line),
                "fgColor": d["serviceJourney"]["line"]["foregroundColor"],
                "bgColor": d["serviceJourney"]["line"]["backgroundColor"],
                "text": time
            }

            for d2 in deps[idx+1:]:
                if int(d2["serviceJourney"]["line"]["shortName"]) == line:
                    time2 = self._time_diff(d2["estimatedOtherwisePlannedTime"])
                    if time2 == "0 m" or time.startswith("-"):
                        time2 = "nu"

                    ld["text"] = ld["text"] + " | " + time2
                    break

            vtdata.append(ld)
            lines = [l for l in lines if l != line]

        self.data = vtdata

    def draw(self, width: int, height: int) -> Surface:
        surface = Surface((width, height), SRCALPHA)

        try:
            self._update_data()
        except Exception as e:
            self.logger.error("cannot update data: %s", e)

        vt_surface_templ = self.font.render("99", True, (255, 255, 255))

        for idx in range(len(self.data)):
            vd = self.data[len(self.data)-1-idx]
            vt_surface = self.font.render(vd["line"], True, vd["fgColor"])
            vt_surfaceText = self.font.render(vd["text"], True, (255, 255, 255))

            vd_width = vt_surface_templ.get_width() + 10
            vd_width_txt = vt_surface.get_width() + 10
            vd_height = vt_surface_templ.get_height() + 10
            rect_vt= Surface((vd_width, vd_height), SRCALPHA)
            pygdraw.rect(rect_vt, vd["bgColor"], rect_vt.get_rect(), border_radius=0)

            h = height - ((vd_height + 10) * (idx+1) - 10)
            surface.blit(rect_vt, (0, h))
            surface.blit(vt_surface, (5 + (vd_width - vd_width_txt)/2, h + 5))
            surface.blit(vt_surfaceText, (5 + vd_width , h + 5))

        return surface



# This function is adapted from https://github.com/axelniklasson/PyTrafik (MIT License)
def fetch_token(key, secret):
    """Fetches a token from the API to use in subsequent calls
    - key:      key from API portal
    - secret:   secret from API portal
    """

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic "
        + base64.b64encode((key + ":" + secret).encode()).decode(),
    }
    data = {"grant_type": "client_credentials"}

    response = requests.post(TOKEN_URL, data=data, headers=headers)
    obj = json.loads(response.content.decode("UTF-8"))
    return obj["access_token"]

# This function is adapted from https://github.com/axelniklasson/PyTrafik (MIT License)
class Client:
    """Client used to communnicate with the API."""
    def __init__(self, response_format, key=CONSUMER_KEY, secret=CONSUMER_SECRET):
        self.token = fetch_token(key, secret)
        self._last_stop_api_call = 0
        self._last_dep_api_call = 0
        if response_format in ["JSON", "json"]:
            self.response_format = "json"
        else:
            self.response_format = ""  # defaulting to XML

    def get_stop_by_name(self, query, query_params=dict()):
        """/location.name endpoint
        - query: name to search for as string
        """
        if timelib.time() - self._last_stop_api_call < 10:
            raise Exception("called api less than 10 seconds ago")

        self._last_stop_api_call = timelib.time()

        query_params["types"] = "stoparea"
        data = self.get("/locations/by-text?q=" + query, query_params)
        if len(data["results"]) > 0:
            return data["results"][0]
        else:
            return None

    # /departureBoard endpoint
    def get_departures(
        self, stop_id, platform, date=None, time=None, query_params=dict()
    ):
        """/departureBoard endpoint
        - stop_id:      stop_id as long
        - date:         the date in format YYYY-MM-DD
        - time:         the time in format HH:MM
        """
        # if date is not None and time is not None:
        if timelib.time() - self._last_dep_api_call < 10:
            raise Exception("called api less than 10 seconds ago")

        self._last_dep_api_call = timelib.time()

        query_params["platforms"] = platform.upper()
        data = self.get(
            "/stop-areas/" + stop_id + "/departures?",
            query_params,
        )
        return data["results"]

    # request builder
    def get(self, endpoint, query_params=None):
        """Helper method to make an HTTP request to the API
        - endpoint: which endpoint to use for the call
        """
        url = API_BASE_URL + endpoint

        if query_params is not None:
            for key in query_params:
                url += "&" + key + "=" + query_params[key]
            url += "&format=" + self.response_format
        elif "?" in url:
            url += "&format=" + self.response_format
        else:
            url += "?format=" + self.response_format

        headers = {"Authorization": "Bearer " + self.token}
        res = requests.get(url, headers=headers)

        if res.status_code == 200:
            return json.loads(res.content.decode("UTF-8"))

        raise Exception("Error: " + str(res.status_code) + str(res.content))
