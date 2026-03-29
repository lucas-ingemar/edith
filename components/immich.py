import logging
import time
from pydantic import BaseModel, AnyUrl, Field
import datetime
from io import BytesIO
import random
from typing import List
from PIL import Image, ImageFile
from pydantic import AnyUrl
from pygame import SRCALPHA, Font, Surface
import pygame
import requests

class ImmichConfig(BaseModel):
    base_url: AnyUrl
    album_id: str = Field(..., min_length=1)
    api_key: str = Field(..., min_length=1)
    show_date: bool
    update_freq: int

class ImmichImage(object):
    def __init__(self, image:ImageFile.ImageFile, assetsResp):
        self.image = image
        self.faces:List[ImmichFace] = []
        self.date:datetime.datetime

        for p in assetsResp["people"]:
            for f in p["faces"]:
                self.faces.append(ImmichFace(f))

        for p in assetsResp["unassignedFaces"]:
            self.faces.append(ImmichFace(p))

        if assetsResp["exifInfo"]:
            if assetsResp["exifInfo"]["dateTimeOriginal"]:
               self.date = datetime.datetime.fromisoformat(assetsResp["exifInfo"]["dateTimeOriginal"])


class ImmichFace(object):
    def __init__(self, faceObject):
        self.boundingBoxX1 = faceObject["boundingBoxX1"]
        self.boundingBoxY1 = faceObject["boundingBoxY1"]
        self.boundingBoxX2 = faceObject["boundingBoxX2"]
        self.boundingBoxY2 = faceObject["boundingBoxY2"]


class Immich(object):
    def __init__(self, cfg: ImmichConfig, date_font: Font):
        self.baseUrl = cfg.base_url
        self.albumID = cfg.album_id
        self.date_font = date_font
        self.headers = {"x-api-key": cfg.api_key, 'Accept': 'application/json'}
        self.logger = logging.getLogger(__name__)
        self.cfg = cfg

        self._image:ImmichImage|None = None
        self._surface:Surface = Surface((0,0))
        self._updated_at = 0

    def get_random_image_from_album(self) -> ImmichImage|None:
        # Fetch album details (includes asset IDs)
        self.logger.info("updating image")
        self._updated_at = time.time()

        url = f"{self.baseUrl}/albums/{self.albumID}"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        album = resp.json()

        if not album["assets"]:
            self.logger.error("No assets found in album")
            return None

        # Pick a random asset
        images = [a for a in album["assets"] if a.get("type") == "IMAGE"]

        if not images:
            self.logger.error("No images found in album")
            return None

        # Pick a random image asset
        asset = random.choice(images)

        asset_url = f"{self.baseUrl}/assets/{asset['id']}"
        asset_resp = requests.get(asset_url, headers=self.headers, stream=True )
        asset_resp.raise_for_status()

        assets = asset_resp.json()

        # Download the original image
        img_url = f"{self.baseUrl}/assets/{asset['id']}/thumbnail?size=preview"
        self.logger.info("downloading image: %s" % img_url)

        img_resp = requests.get(img_url, headers=self.headers, stream=True )
        img_resp.raise_for_status()

        immichImg = ImmichImage(Image.open(BytesIO(img_resp.content)), assets)

        return immichImg

    def _pygame_image(self, screen_size):
        if self._image is None:
            self.logger.error("cannot create pygame image, no immich image loaded")
            return None

        img = self._image.image.convert("RGB")
        screen_width, screen_height = screen_size
        img_width, img_height = img.size

        # Compute scale factor
        scale = max(screen_width / img_width, screen_height / img_height)
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)

        img = img.resize((new_width, new_height), Image.LANCZOS)

        # Default center
        crop_cx = new_width / 2
        crop_cy = new_height / 2

        # If faces exist → compute mean center
        if self._image.faces:
            mean = self._get_mean_face_center(self._image.faces)
            if mean:
                mean_x, mean_y = mean
                crop_cx = mean_x * scale
                crop_cy = mean_y * scale

        # Convert center → crop box
        left = int(crop_cx - screen_width / 2)
        top = int(crop_cy - screen_height / 2)

        # Clamp to image bounds
        left = max(0, min(left, new_width - screen_width))
        top = max(0, min(top, new_height - screen_height))

        right = left + screen_width
        bottom = top + screen_height

        img = img.crop((left, top, right, bottom))

        return pygame.image.frombytes(img.tobytes(), img.size, img.mode)

    def _get_mean_face_center(self, faces: List[ImmichFace]):
        if not faces:
            return None

        centers = []
        for f in faces:
            cx = (f.boundingBoxX1 + f.boundingBoxX2) / 2
            cy = (f.boundingBoxY1 + f.boundingBoxY2) / 2
            centers.append((cx, cy))

        mean_x = sum(c[0] for c in centers) / len(centers)
        mean_y = sum(c[1] for c in centers) / len(centers)

        return mean_x, mean_y

    def _blur_surface(self, surface, passes=3, scale=0.5):
        w, h = surface.get_size()
        surf = surface.copy()

        for _ in range(passes):
            surf = pygame.transform.smoothscale(surf, (int(w * scale), int(h * scale)))
            surf = pygame.transform.smoothscale(surf, (w, h))

        return surf

    def _add_menu(self, menu_width: int, blur: bool):
        rect = pygame.Rect(0, 0, menu_width, self._surface.get_height())

        sub = self._surface.subsurface(rect).copy()

        menu_opacity = 180
        if blur:
            blurred = self._blur_surface(sub, passes=5, scale=0.2)
            menu_opacity = 80
        else:
            blurred = sub

        self._surface.blit(blurred, rect.topleft)#

        overlay = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, menu_opacity))
        self._surface.blit(overlay, rect.topleft)

    def _add_date(self):
        if self._image is None:
            return

        imgtime_shadow = self.date_font.render(self._image.date.strftime("%y-%m-%d"), True, (231, 126, 0))
        imgtime_surface = self.date_font.render(self._image.date.strftime("%y-%m-%d"), True, (251, 146, 20))
        it_width= imgtime_surface.get_width() + 30
        it_height = imgtime_surface.get_height() + 30

        self._surface.blit(imgtime_shadow, (self._surface.get_width()-it_width + 1, self._surface.get_height()-it_height +1 ))
        self._surface.blit(imgtime_surface, (self._surface.get_width()-it_width, self._surface.get_height()-it_height))

    def _update_surface(self, screen: Surface, blur: bool, menu_width: int):
        background = self._pygame_image((screen.get_width(), screen.get_height()))
        self._surface = Surface((screen.get_width(), screen.get_height()), SRCALPHA)

        if background:
            self._surface.blit(background, (0, 0))
        else:
            self._surface.fill((0, 0, 0))

        self._add_menu(menu_width, blur)

        if self.cfg.show_date:
            self._add_date()

    def draw_background(self, screen: Surface, blur: bool, menu_width: int):
        updated = False
        if time.time() - self._updated_at >= self.cfg.update_freq:
            self._image = self.get_random_image_from_album()
            updated = True

        if updated or self._surface.get_width() != screen.get_width() or self._surface.get_height() != screen.get_height():
            self._update_surface(screen, blur, menu_width)

        screen.blit(self._surface, (0, 0))
