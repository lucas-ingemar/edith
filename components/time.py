#!/usr/bin/env python3


from datetime import datetime
from pygame import SRCALPHA, Font, Surface


class Time(object):
    def __init__(self, time_font: Font, date_font: Font):
        self.time_font = time_font
        self.date_font = date_font
        pass

    @classmethod
    def block_count(cls) -> int:
        return 3

    def draw(self, width: int, height: int) -> Surface:
        surface = Surface((width, height), SRCALPHA)

        now = datetime.now()
        time_str = now.strftime("%H:%M")
        date_str = now.strftime("%Y-%m-%d")

        t_surface = self.time_font.render(time_str, True, (255, 255, 255))
        d_surface = self.date_font.render(date_str, True, (255, 255, 255))

        surface.blit(t_surface, (0, 0))
        surface.blit(d_surface, (0, t_surface.get_height() + 5))

        return surface
