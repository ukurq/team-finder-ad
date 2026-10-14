import random
import uuid
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont

from .constants import AVATAR_BACKGROUNDS, AVATAR_SIZE

FONT_PATH = (
    Path(settings.BASE_DIR)
    / "static"
    / "fonts"
    / "Neue_Haas_Grotesk_Display_Pro_75_Bold.otf"
)


def _load_font(size):
    try:
        return ImageFont.truetype(str(FONT_PATH), size)
    except OSError:
        return ImageFont.load_default(size)


def generate_avatar(name):
    """Создаёт аватарку: первая буква имени на однотонном фоне."""
    letter = (name.strip()[:1] or "?").upper()
    image = Image.new(
        "RGB", (AVATAR_SIZE, AVATAR_SIZE), random.choice(AVATAR_BACKGROUNDS)
    )
    ImageDraw.Draw(image).text(
        (AVATAR_SIZE / 2, AVATAR_SIZE / 2),
        letter,
        font=_load_font(AVATAR_SIZE // 2),
        fill="white",
        anchor="mm",
    )
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return ContentFile(buffer.getvalue(), name=f"avatar_{uuid.uuid4()}.png")
