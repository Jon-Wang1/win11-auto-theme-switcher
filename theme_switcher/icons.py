"""Programmatic icon generation — no external icon files needed."""

from PIL import Image, ImageDraw


def generate_sun_icon() -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    r = 12
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 200, 50, 255))

    ray_len_outer = 20
    ray_len_inner = 15
    ray_width = 3
    for angle in range(0, 360, 45):
        import math
        rad = math.radians(angle)
        x1 = cx + (r + 1) * math.cos(rad)
        y1 = cy + (r + 1) * math.sin(rad)
        x2 = cx + ray_len_outer * math.cos(rad)
        y2 = cy + ray_len_outer * math.sin(rad)
        draw.line([x1, y1, x2, y2], fill=(255, 200, 50, 255), width=ray_width)

    return img


def generate_moon_icon() -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    r = 14
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(200, 200, 220, 255))
    draw.ellipse([cx - r - 4, cy - r - 2, cx + r - 4, cy + r - 2], fill=(0, 0, 0, 0))

    return img


def generate_auto_icon() -> Image.Image:
    return generate_sun_icon()


def get_icon_for_state(auto_mode: bool, current_theme: str) -> Image.Image:
    if current_theme == "light":
        return generate_sun_icon()
    return generate_moon_icon()
