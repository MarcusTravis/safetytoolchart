#!/usr/bin/env python3
"""One-off: draws favicon.svg, favicon.ico, apple-touch-icon.png and og-image.png (original line art, needs Pillow).

Motif: an overhead anchor bar, a short lanyard line, and a harness D-ring.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
BG, TEAL, ICE, STEEL, AMBER = (5, 13, 22), (63, 193, 201), (155, 231, 234), (143, 180, 200), (245, 179, 53)

(ROOT / "favicon.svg").write_text("""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="6" fill="#071622"/>
  <rect x="1" y="1" width="30" height="30" rx="5" fill="none" stroke="#3fc1c9" stroke-width="1.5"/>
  <path d="M6 7.5 H26" stroke="#9be7ea" stroke-width="2.2" stroke-linecap="round"/>
  <path d="M16 7.5 V15" stroke="#3fc1c9" stroke-width="1.8"/>
  <path d="M16 15 c-2.2 1.4 2.2 2.6 0 4" fill="none" stroke="#3fc1c9" stroke-width="1.6"/>
  <path d="M12 19.5 h8 c0 3.8 -1.8 6 -4 6 s-4 -2.2 -4 -6 z" fill="none" stroke="#9be7ea" stroke-width="1.9" stroke-linejoin="round"/>
</svg>
""")


def d_ring(d, cx, top, w, h, fill, width):
    """Flat bar on top, rounded 'D' below."""
    d.line([(cx - w / 2, top), (cx + w / 2, top)], fill=fill, width=width)
    d.arc([cx - w / 2, top - h, cx + w / 2, top + h], 0, 180, fill=fill, width=width)


def icon(size):
    s = 8  # supersample
    N = size * s
    im = Image.new("RGB", (N, N), (7, 22, 34))
    d = ImageDraw.Draw(im)
    lw = max(2, N // 18)
    d.rounded_rectangle([N * .03, N * .03, N * .97, N * .97], radius=N * .17, outline=TEAL, width=max(2, N // 22))
    d.line([(N * .2, N * .24), (N * .8, N * .24)], fill=ICE, width=lw)            # anchor bar
    d.line([(N * .5, N * .24), (N * .5, N * .46)], fill=TEAL, width=lw)           # lanyard
    d.line([(N * .5, N * .46), (N * .44, N * .52), (N * .56, N * .56), (N * .5, N * .6)], fill=TEAL, width=max(2, N // 24), joint="curve")  # absorber zigzag
    d_ring(d, N * .5, N * .62, N * .3, N * .2, ICE, lw)                           # D-ring
    return im.resize((size, size), Image.LANCZOS)


icon(180).save(ROOT / "apple-touch-icon.png")
icon(256).save(ROOT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])


def font(size, bold=True):
    for n in (("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), ("LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf")):
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            pass
    return ImageFont.load_default(size)


W, Hh = 1200, 630
og = Image.new("RGB", (W, Hh), BG)
d = ImageDraw.Draw(og)
for y in range(Hh):  # night-sky gradient
    t = y / Hh
    d.line([(0, y), (W, y)], fill=(int(5 + 5 * (1 - t)), int(13 + 22 * (1 - t)), int(22 + 32 * (1 - t))))
# overhead I-beam
for y in (60, 70, 104, 114):
    d.line([(640, y), (W, y)], fill=ICE, width=3)
d.line([(640, 60), (640, 70)], fill=ICE, width=3); d.line([(640, 104), (640, 114)], fill=ICE, width=3)
# beam clamp
d.line([(880, 122), (868, 122), (868, 50), (884, 38)], fill=TEAL, width=4, joint="curve")
d.line([(960, 122), (972, 122), (972, 50), (956, 38)], fill=TEAL, width=4, joint="curve")
d.line([(868, 98), (972, 98)], fill=TEAL, width=4)
d.line([(920, 122), (920, 140)], fill=TEAL, width=4)
d.ellipse([906, 140, 934, 172], outline=TEAL, width=4)
# lanyard with energy-absorber pack
d.line([(920, 172), (920, 250)], fill=TEAL, width=4)
d.rounded_rectangle([900, 250, 940, 330], radius=12, outline=ICE, width=4)
d.line([(920, 330), (920, 400)], fill=TEAL, width=4)
# harness straps + D-ring
d.line([(860, 380), (980, 540)], fill=TEAL, width=5)
d.line([(980, 380), (860, 540)], fill=TEAL, width=5)
d_ring(d, 920, 410, 52, 36, ICE, 6)
# clearance scale
d.line([(1100, 120), (1100, 600)], fill=STEEL, width=2)
for y in range(120, 601, 80):
    d.line([(1088, y), (1112, y)], fill=STEEL, width=2)
# edge hatching
d.line([(640, 560), (820, 560)], fill=STEEL, width=3)
for x in range(650, 820, 28):
    d.line([(x, 560), (x + 14, 540)], fill=AMBER, width=5)
d.text((60, 170), "Safety", font=font(104), fill=(233, 243, 248))
d.text((60, 285), "Tool Chart", font=font(84), fill=ICE)
d.text((62, 400), "Harnesses · lanyards · SRLs · anchors", font=font(32, False), fill=STEEL)
d.text((62, 445), "Fall protection compared · free and ad-free", font=font(30, False), fill=TEAL)
d.text((62, 560), "safetytoolchart.pages.dev", font=font(28, False), fill=STEEL)
og.save(ROOT / "og-image.png")
print("assets written")
