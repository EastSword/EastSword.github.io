"""Feather the banner edges while retaining the original figure detail."""

from pathlib import Path

from PIL import Image


def smoothstep(value):
    value = min(1, max(0, value))
    return value * value * (3 - 2 * value)


directory = Path(__file__).resolve().parents[1] / 'assets/images/hero'
image = Image.open(directory / 'warrior-original.webp').convert('RGBA')
width, height = image.size
alpha = Image.new('L', image.size)
alpha.putdata([
    round(255
          * smoothstep((x / width - .18) / .36)
          * smoothstep(y / (height * .10))
          * smoothstep((height - 1 - y) / (height * .16))
          * smoothstep((width - 1 - x) / (width * .065)))
    for y in range(height)
    for x in range(width)
])
image.putalpha(alpha)
image.save(directory / 'warrior-inkwash.webp', quality=91, method=6)
