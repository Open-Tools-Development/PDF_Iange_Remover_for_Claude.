#!/usr/bin/env python3
"""Generate icon.ico and splash.png for the PDF Image Remover tool."""
import os
from PIL import Image, ImageDraw, ImageFont

FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


# Palette
BG = (15, 23, 42)          # slate-900
PANEL = (30, 41, 59)       # slate-800
ACCENT = (56, 189, 248)    # sky-400
ACCENT2 = (251, 191, 36)   # amber-400
RED = (239, 68, 68)        # red-500
WHITE = (241, 245, 249)
MUTED = (148, 163, 184)
GREEN = (74, 222, 128)


def rounded(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


# --------------------------------------------------------------------------- #
#  ICON  - a PDF page; top: an image thumbnail struck through (removed);       #
#          bottom: text lines + a small "TeX" tag (convert). Purpose at glance #
# --------------------------------------------------------------------------- #
def make_icon(path, size=256):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 256.0

    # Rounded app tile background.
    rounded(d, [int(8 * s), int(8 * s), int(248 * s), int(248 * s)],
            int(48 * s), fill=BG)

    # White document page with a folded corner.
    px0, py0, px1, py1 = int(64 * s), int(40 * s), int(192 * s), int(216 * s)
    fold = int(34 * s)
    page = [(px0, py0), (px1 - fold, py0), (px1, py0 + fold), (px1, py1),
            (px0, py1)]
    d.polygon(page, fill=WHITE)
    d.polygon([(px1 - fold, py0), (px1, py0 + fold), (px1 - fold, py0 + fold)],
              fill=MUTED)

    # Top: small image thumbnail (sky) with sun + mountain, then a red strike.
    ix0, iy0, ix1, iy1 = int(80 * s), int(64 * s), int(176 * s), int(120 * s)
    rounded(d, [ix0, iy0, ix1, iy1], int(8 * s), fill=ACCENT)
    # sun
    d.ellipse([ix0 + int(10 * s), iy0 + int(10 * s),
               ix0 + int(28 * s), iy0 + int(28 * s)], fill=ACCENT2)
    # mountains
    d.polygon([(ix0 + int(8 * s), iy1 - int(6 * s)),
               (ix0 + int(40 * s), iy0 + int(26 * s)),
               (ix0 + int(70 * s), iy1 - int(6 * s))], fill=PANEL)
    d.polygon([(ix0 + int(46 * s), iy1 - int(6 * s)),
               (ix0 + int(72 * s), iy0 + int(30 * s)),
               (ix1 - int(8 * s), iy1 - int(6 * s))], fill=(51, 65, 85))
    # red diagonal strike-through = "image removed"
    d.line([(ix0 - int(4 * s), iy1 + int(2 * s)),
            (ix1 + int(4 * s), iy0 - int(2 * s))],
           fill=RED, width=int(10 * s))

    # Bottom: text lines (the recovered text) + TeX tag.
    ly = int(136 * s)
    for w in (96, 96, 80):
        rounded(d, [int(80 * s), ly, int(80 * s) + int(w * s), ly + int(8 * s)],
                int(4 * s), fill=MUTED)
        ly += int(18 * s)
    # "TeX" tag
    rounded(d, [int(120 * s), int(186 * s), int(176 * s), int(208 * s)],
            int(6 * s), fill=ACCENT)
    try:
        tf = font("DejaVuSans-Bold.ttf", int(16 * s))
    except Exception:
        tf = ImageFont.load_default()
    d.text((int(130 * s), int(189 * s)), "TeX", font=tf, fill=BG)

    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128),
             (256, 256)]
    img.save(path, format="ICO", sizes=sizes)
    # Also a PNG preview.
    img.save(os.path.splitext(path)[0] + "_preview.png")


# --------------------------------------------------------------------------- #
#  SPLASH                                                                      #
# --------------------------------------------------------------------------- #
def make_splash(path, version, w=620, h=380):
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)

    # Accent side bar.
    d.rectangle([0, 0, 8, h], fill=ACCENT)
    # Subtle panel header.
    d.rectangle([0, 0, w, 96], fill=PANEL)

    f_title = font("DejaVuSans-Bold.ttf", 30)
    f_sub = font("DejaVuSans.ttf", 15)
    f_small = font("DejaVuSans.ttf", 13)
    f_tiny = font("DejaVuSans.ttf", 12)
    f_author = font("DejaVuSans-Bold.ttf", 15)

    # Mini icon at top-left of header.
    icon = Image.open("icon_preview.png").convert("RGBA").resize((68, 68))
    img.paste(icon, (26, 14), icon)

    d.text((108, 24), "PDF Image Remover", font=f_title, fill=WHITE)
    d.text((110, 62), "Image Remover  \u00b7  LaTeX  \u00b7  Markdown converter",
           font=f_sub, fill=ACCENT)

    # Body description.
    y = 120
    desc = [
        "Strip images from PDFs (keeping text & layout), or convert a paper",
        "into clean, compilable IEEE LaTeX or full-text Markdown \u2014 ready",
        "for any AI tool to read without processing the PDF.",
    ]
    for line in desc:
        d.text((30, y), line, font=f_small, fill=MUTED)
        y += 22

    # Feature chips.
    y += 12
    chips = ["Remove images", "PDF \u2192 LaTeX", "PDF \u2192 Markdown"]
    cx = 30
    for c in chips:
        tw = d.textlength(c, font=f_tiny)
        rounded(d, [cx, y, cx + tw + 24, y + 28], 14, fill=(2, 6, 23),
                outline=ACCENT, width=1)
        d.text((cx + 12, y + 7), c, font=f_tiny, fill=ACCENT)
        cx += tw + 36

    # Footer: author + license + version.
    d.line([30, h - 64, w - 24, h - 64], fill=(51, 65, 85), width=1)
    d.text((30, h - 52), "by Jerry James", font=f_author, fill=WHITE)
    d.text((30, h - 30), "Open source \u00b7 GPL-3.0 License", font=f_tiny,
           fill=MUTED)
    vtext = f"v{version}"
    d.text((w - 24 - d.textlength(vtext, font=f_small), h - 50), vtext,
           font=f_small, fill=ACCENT2)
    load = "Starting\u2026"
    d.text((w - 24 - d.textlength(load, font=f_tiny), h - 28), load,
           font=f_tiny, fill=MUTED)

    img.save(path)


if __name__ == "__main__":
    import about_info
    make_icon("icon.ico")
    make_splash("splash.png", about_info.VERSION)
    print("Generated icon.ico, icon_preview.png, splash.png")
