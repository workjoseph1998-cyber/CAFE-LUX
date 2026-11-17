"""Draw original lightweight sample artwork; never reads/edits owner images.

Pillow is already a production dependency. Output is illustrative, not product
photography or approved packaging. Re-run only when deliberately updating art.
"""

import math
import random
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cafe.starter_catalog import DRINKS, COFFEE

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "cafe" / "static" / "images" / "starter-samples"


def artwork(slug, name, kind, cold=False):
    width, height = 480, 400
    img = Image.new("RGB", (width, height))
    pixels = img.load()
    for y in range(height):
        for x in range(width):
            light = max(0, 1 - math.hypot((x - 200) / 600, (y - 130) / 530))
            pixels[x, y] = (
                int(223 + 24 * light),
                int(208 + 29 * light),
                int(187 + 37 * light),
            )
    d = ImageDraw.Draw(img)
    d.ellipse((75, 285, 410, 355), fill="#d3bfa5")
    if kind == "ground":
        color = {
            "lux-lebanese": "#6b4a36",
            "lux-signature": "#292722",
            "lux-espresso": "#403128",
            "lux-golden": "#9a713e",
        }[slug]
        d.polygon([(148, 77), (328, 77), (342, 310), (137, 310)], fill=color)
        d.rectangle((148, 69, 328, 91), fill="#302a24")
        d.line((155, 100, 320, 100), fill="#b49a70", width=2)
        d.rectangle((165, 138, 310, 244), outline="#c6a56d", width=2)
        d.ellipse((220, 152, 247, 184), fill="#c6a56d")
        d.arc((221, 152, 250, 184), 85, 260, fill=color, width=3)
        # Generic sample branding; never represents the owner's actual package.
        d.text((210, 194), "LUX", fill="#ead6b0")
        d.text((193, 215), "SAMPLE BLEND", fill="#c8ad81")
        d.line(
            (160, 270, 188, 251, 215, 275, 239, 253, 265, 272, 296, 249, 324, 271),
            fill="#b99b66",
            width=2,
        )
    elif cold:
        d.polygon(
            [(164, 108), (316, 108), (300, 306), (180, 306)],
            fill="#bfa184",
            outline="#8c725e",
        )
        dark = "americano" in slug or slug == "cold-brew"
        d.polygon(
            [(169, 127), (311, 127), (297, 303), (183, 303)],
            fill="#593626" if dark else "#c58c59",
        )
        if not dark:
            d.polygon([(176, 210), (304, 204), (298, 295), (183, 295)], fill="#e2c09b")
            d.line((178, 203, 305, 200), fill="#b37543", width=9)
        for x, y in [(183, 144), (229, 134), (265, 160), (207, 176)]:
            d.rounded_rectangle(
                (x, y, x + 28, y + 24),
                radius=5,
                fill="#e8d9c4",
                outline="#f9f4e8",
                width=2,
            )
        d.ellipse((163, 96, 317, 123), outline="#f7eee0", width=4)
        d.line((284, 65, 262, 270), fill="#785b46", width=7)
        d.line((288, 65, 266, 266), fill="#dec6a5", width=2)
        d.line((183, 121, 197, 287), fill="#f4e6d7", width=3)
    else:
        small = slug in {
            "espresso",
            "double-espresso",
            "macchiato",
            "cortado",
            "lebanese-coffee",
            "lebanese-cardamom",
            "turkish-coffee",
        }
        left, right, top, bottom = (
            (170, 302, 172, 285) if small else (140, 320, 143, 290)
        )
        d.ellipse((left - 35, bottom - 8, right + 55, bottom + 35), fill="#b99b7c")
        d.ellipse(
            (left - 30, bottom - 12, right + 50, bottom + 28),
            fill="#f6ead9",
            outline="#c9b497",
            width=2,
        )
        d.ellipse(
            (right - 19, top + 21, right + 63, bottom - 20), outline="#c1a78c", width=17
        )
        d.ellipse(
            (right - 16, top + 22, right + 60, bottom - 22), outline="#eee0cb", width=10
        )
        d.rounded_rectangle(
            (left, top, right, bottom),
            radius=37,
            fill="#f2e5cf",
            outline="#bca080",
            width=2,
        )
        d.ellipse(
            (left, top - 17, right, top + 25),
            fill="#e7d6bd",
            outline="#aa8b69",
            width=2,
        )
        milk = slug in {
            "cappuccino",
            "caffe-latte",
            "flat-white",
            "mocha",
            "spanish-latte",
            "cortado",
            "macchiato",
        }
        d.ellipse(
            (left + 8, top - 10, right - 8, top + 18),
            fill="#bc7b3c" if milk else "#43271a",
        )
        if milk:
            center = (left + right) // 2
            for delta in range(5):
                spread = 24 - delta * 4
                d.arc(
                    (
                        center - spread,
                        top - 8 + delta * 2,
                        center + spread,
                        top + 13 + delta * 2,
                    ),
                    0,
                    180,
                    fill="#fff2d9",
                    width=2,
                )
            d.line((center, top - 5, center + 3, top + 17), fill="#fff2d9", width=2)
        for offset in [0, 28, 54]:
            x = left + 28 + offset
            d.arc((x, top - 76, x + 20, top - 28), 90, 265, fill="#faf5ed", width=3)
    rng = random.Random(slug)
    for n in range(5):
        x = rng.randint(55, 405)
        y = rng.randint(330, 355)
        d.ellipse((x, y, x + 12, y + 8), fill="#745139")
        d.line((x + 2, y + 6, x + 10, y + 2), fill="#c49a70", width=1)
    # Visible in the file itself and in the preview UI.
    d.rounded_rectangle((16, 16, 180, 41), radius=4, fill="#f8f4ed")
    d.text((27, 23), "SAMPLE ILLUSTRATION", fill="#70533e")
    d.text((18, 375), "CAFÉ LUX  /  CATALOG PREVIEW", fill="#795b45")
    return img


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for _, _, items in DRINKS:
        for slug, name, description, size, temp in items:
            artwork(slug, name, "drink", temp == "cold").save(
                OUTPUT / (slug + ".jpg"),
                "JPEG",
                quality=78,
                optimize=True,
                progressive=True,
            )
    for _, _, slug, name, description, types in COFFEE:
        artwork(slug, name, "ground").save(
            OUTPUT / (slug + ".jpg"),
            "JPEG",
            quality=78,
            optimize=True,
            progressive=True,
        )
    files = list(OUTPUT.glob("*.jpg"))
    print(
        f"{len(files)} original sample illustrations; {sum(p.stat().st_size for p in files):,} bytes total; max {max(p.stat().st_size for p in files):,} bytes."
    )


if __name__ == "__main__":
    main()
