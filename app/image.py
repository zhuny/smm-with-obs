import base64
from io import BytesIO

from PIL import Image


class PillowImageWrapper:
    def __init__(self, image):
        self.main_image = image
        self.mode_cache = {image.mode: image}

    @classmethod
    def load_from_base64(cls, image_data):
        screen_data = base64.b64decode(image_data)
        image = Image.open(BytesIO(screen_data))
        return cls(image)

    def get_by_mode(self, mode):
        if mode not in self.mode_cache:
            self.mode_cache[mode] = self.main_image.convert(mode)
        return self.mode_cache[mode]

    def total_pixel(self):
        width, height = self.main_image.size
        return width * height
