"""Generate ikon PWA + og.png dari desain ikon Presetly (huruf P + titik cyan).

Jalanin: python tools/gen_icons.py  (output ke web/public/)
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "web" / "public"
BG = (7, 6, 11)
GRAD_A = (196, 181, 253)  # #c4b5fd
GRAD_B = (139, 92, 246)  # #8b5cf6
CYAN = (95, 243, 248)  # #5ff3f8
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw_mark(size: int, rounded: bool = True, pad: float = 0.0) -> Image.Image:
    """Ikon P: rounded square gelap, huruf P gradient, titik cyan. pad = ruang aman (maskable)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = size * 0.25 if rounded else 0
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=BG + (255,))
    if rounded:
        d.rounded_rectangle(
            [size * 0.03, size * 0.03, size * 0.97, size * 0.97],
            radius=r * 0.85,
            outline=GRAD_A + (128,),
            width=max(2, size // 32),
        )
    s = size * (1 - 2 * pad)  # area gambar setelah padding aman
    o = size * pad  # offset
    lw = max(3, round(s * 0.078))
    # koordinat desain viewBox 64 -> skala s/64
    k = s / 64

    def P(x, y):
        return (o + x * k, o + y * k)

    # gradient stroke: gambar P sebagai SATU polyline (stem + bowl busur) biar sambungan mulus
    mark = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dm = ImageDraw.Draw(mark)

    cx0, cy0 = P(33.5, 25.5)  # pusat busur bowl
    r0 = (42 - 25) / 2 * k
    pts = [P(22, 48), P(22, 17), P(33.5, 17)]
    for i in range(1, 25):  # busur dari atas (12 jam) ke bawah (6 jam) lewat kanan
        a = math.radians(-90 + 180 * i / 24)
        pts.append((cx0 + r0 * math.cos(a), cy0 + r0 * math.sin(a)))
    pts += [P(22, 34)]
    dm.line(pts, fill=GRAD_B + (255,), width=lw, joint="curve")
    # haluskan ujung: lingkaran kecil di titik ujung
    for p in (P(22, 48), P(22, 34)):
        dm.ellipse([p[0] - lw / 2, p[1] - lw / 2, p[0] + lw / 2, p[1] + lw / 2], fill=GRAD_B + (255,))
    grad = Image.new("RGBA", (size, size))
    dg = ImageDraw.Draw(grad)
    for y in range(size):
        dg.line([(0, y), (size, y)], fill=_lerp(GRAD_A, GRAD_B, y / size) + (255,))
    mark.putalpha(Image.composite(mark.getchannel("A"), Image.new("L", (size, size), 0), mark.getchannel("A")))
    img.paste(grad, (0, 0), mark)
    # titik cyan
    cx, cy = P(47, 17)
    cr = max(3, s * 0.062)
    d = ImageDraw.Draw(img)
    d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=CYAN + (255,))
    return img


def gen_icons():
    draw_mark(192).save(OUT / "icon-192.png")
    draw_mark(512).save(OUT / "icon-512.png")
    draw_mark(512, rounded=False, pad=0.1).save(OUT / "icon-maskable-512.png")
    draw_mark(180, rounded=False).save(OUT / "apple-touch-icon.png")
    print("icons OK")


def gen_og():
    w, h = 1200, 630
    img = Image.new("RGBA", (w, h), BG + (255,))
    # glow violet lembut di tengah
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dg = ImageDraw.Draw(glow)
    for i in range(46):
        rx, ry = 620 - i * 11, 320 - i * 6
        a = max(1, 7 - i // 7)
        dg.ellipse([w / 2 - rx, h / 2 - 40 - ry, w / 2 + rx, h / 2 - 40 + ry], fill=GRAD_B[:3] + (a,))
    img = Image.alpha_composite(img, glow)
    d = ImageDraw.Draw(img)
    # kartu ikon
    mark = draw_mark(132)
    img.paste(mark, (w // 2 - 66, 118), mark)
    # wordmark
    f_big = ImageFont.truetype(FONT_BOLD, 78)
    f_mid = ImageFont.truetype(FONT_REG, 31)
    f_small = ImageFont.truetype(FONT_BOLD, 22)
    title = "Presetly"
    tw = d.textlength(title, font=f_big)
    ty = 286
    # warna gradient sederhana: teks utama lavender terang
    d.text(((w - tw) / 2, ty), title, font=f_big, fill=GRAD_A)
    sub = "Cari preset Alight Motion dari YouTube & TikTok"
    sw = d.textlength(sub, font=f_mid)
    d.text(((w - sw) / 2, ty + 104), sub, font=f_mid, fill=(160, 155, 185))
    foot = "BUILT-IN XYVERSE  ·  PRESETLY.VERCEL.APP"
    fw = d.textlength(foot, font=f_small)
    d.text(((w - fw) / 2, h - 70), foot, font=f_small, fill=(110, 105, 135))
    # garis aksen
    d.line([(w / 2 - 30, ty + 92), (w / 2 + 30, ty + 92)], fill=CYAN, width=3)
    img.convert("RGB").save(OUT / "og.png", optimize=True)
    print("og OK")


if __name__ == "__main__":
    gen_icons()
    gen_og()
