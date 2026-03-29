import argparse
import logging
from components import Immich, Hass, Time, Vasttrafik
import config
import pygame
import sys
import time

class ScreenCfg(object):
    def __init__(self):
        self.menu_width = 165
        self.padding_x = 20
        self.padding_y = 20
        self.blocks = 15
        self.block_height = 0
        self.block_width = 0

    def update(self, screen: pygame.Surface):
        self.block_height = int((screen.height - 2*self.padding_y) / self.blocks)
        self.block_width = self.menu_width - 2*self.padding_x


def draw(screen: pygame.Surface, screenCfg: ScreenCfg, cfg: config.Config, immichCmp: Immich, timeCmp: Time, hassCmp: Hass, vtCmp:Vasttrafik):
    screenCfg.update(screen)

    immichCmp.draw_background(screen, cfg.general.blur, screenCfg.menu_width)

    # CLOCK
    timeSurface = timeCmp.draw(screenCfg.block_width, screenCfg.block_height * timeCmp.block_count())
    screen.blit(timeSurface, (screenCfg.padding_x, screenCfg.padding_y + 0*screenCfg.block_height))

    # HASS
    hassSurface = hassCmp.draw(screenCfg.block_width, screenCfg.block_height)
    screen.blit(hassSurface, (screenCfg.padding_x, screenCfg.padding_y + 4*screenCfg.block_height))

    # Vasttrafik
    vtSurface = vtCmp.draw(screenCfg.block_width, vtCmp.block_count() * screenCfg.block_height)
    screen.blit(vtSurface, (screenCfg.padding_x, screenCfg.padding_y + 11*screenCfg.block_height))


    pygame.display.flip()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true", help="Enable dev mode")

    args = parser.parse_args()

    loglevel = logging.INFO
    if args.dev:
        loglevel = logging.DEBUG

    logging.basicConfig(
        level=loglevel,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )


    cfg = config.get_config("config.toml")
    screenCfg = ScreenCfg()

    pygame.init()
    pygame.font.init()
    pygame.event.clear()

    if args.dev:
        screen = pygame.display.set_mode((800,480), pygame.SHOWN)
    else:
        screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)

    pygame.display.set_caption("Clock Screensaver")

    font = pygame.font.SysFont("DejaVu Sans", 50)
    small_font = pygame.font.SysFont("DejaVu Sans", 24)
    vt_font = pygame.font.SysFont("DejaVu Sans", 17)
    image_time_font = pygame.font.Font("fonts/7segment.ttf", 22)

    immichCmp = Immich(cfg.immich, image_time_font)
    hassCmp = Hass(cfg.hass, small_font)
    timeCmp = Time(font, small_font)
    vtCmp = Vasttrafik(vt_font, cfg.vasttrafik)

    clock = pygame.time.Clock()

    start_time = time.time()
    last_draw = 0
    last_bg = time.time()
    last_vt = time.time()

    while True:
        for event in pygame.event.get():
            if time.time() - start_time > 1:
                if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION):
                    pygame.quit()
                    sys.exit()

        if time.time() - last_draw >= 1:
            draw(screen, screenCfg, cfg, immichCmp, timeCmp, hassCmp,vtCmp)
            last_draw = time.time()

        clock.tick(100)
