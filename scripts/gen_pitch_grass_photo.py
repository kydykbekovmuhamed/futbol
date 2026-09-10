"""
v2 — более реалистичная трава: тейперные (сужающиеся к кончику) травинки
вместо однородных линий, пятнистая цветовая вариация через низкочастотный
шум (имитация неровного освещения/окраски настоящего газона), боке-блики
на размытом заднем плане, лёгкая тёплая подсветка по диагонали, резкость
переднего плана после даунскейла — против плоской v1.
"""
import random
import math
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

random.seed(11)

SCALE = 2
W, H = 960, 400
BW, BH = W * SCALE, H * SCALE

img = Image.new("RGB", (BW, BH), "#142418")
draw = ImageDraw.Draw(img)

top_c = (16, 30, 21)
bot_c = (36, 70, 42)
for y in range(BH):
    t = y / BH
    r = int(top_c[0] + (bot_c[0] - top_c[0]) * t)
    g = int(top_c[1] + (bot_c[1] - top_c[1]) * t)
    b = int(top_c[2] + (bot_c[2] - top_c[2]) * t)
    draw.line([(0, y), (BW, y)], fill=(r, g, b))

# --- низкочастотное "пятнистое" поле освещения/окраски: маленький шум-
#     градиент, растянутый бикубикой до полного размера — даёт мягкие пятна
#     светлее/темнее, как неровный свет на настоящем газоне ---
patch = Image.effect_noise((24, 10), 40).convert("L").resize((BW, BH), Image.BICUBIC)
patch = patch.filter(ImageFilter.GaussianBlur(radius=30 * SCALE))

BLADE_BASE = [
    (22, 42, 27), (28, 52, 33), (34, 60, 38),
    (42, 72, 46), (50, 82, 52), (60, 94, 60), (70, 104, 66),
]

def tapered_blade(draw_ctx, x, y, dx, dy, base_w, color):
    """Рисует травинку сужающейся к кончику полигоном, а не однородной линией."""
    length = math.hypot(dx, dy)
    if length < 0.5:
        return
    nx, ny = -dy / length, dx / length  # нормаль
    bw = base_w / 2
    tipx, tipy = x + dx, y + dy
    poly = [
        (x - nx * bw, y - ny * bw),
        (x + nx * bw, y + ny * bw),
        (tipx, tipy),
    ]
    draw_ctx.polygon(poly, fill=color)

N = 30000
patch_px = patch.load()
for _ in range(N):
    x = random.uniform(-10, BW + 10)
    y = random.uniform(BH * 0.16, BH)
    depth = y / BH
    length = random.uniform(7, 17) * (0.45 + depth) * SCALE
    angle = random.uniform(76, 104)
    rad = math.radians(angle)
    dx = length * math.cos(rad)
    dy = -length * math.sin(rad)

    lum = patch_px[min(int(x), BW - 1), min(int(y), BH - 1)] / 255.0  # 0..1 пятно
    color = random.choice(BLADE_BASE)
    k = 0.82 + lum * 0.36  # темнее/светлее по пятну освещения
    color = tuple(min(255, int(c * k)) for c in color)

    base_w = max(1.1, (0.9 + depth * 1.6) * SCALE)
    tapered_blade(draw, x, y, dx, dy, base_w, color)

# --- зернистость ---
noise = Image.effect_noise((BW, BH), 20).convert("L")
noise_rgb = Image.merge("RGB", (noise, noise, noise))
img = Image.blend(img, noise_rgb, 0.035)

# --- тёплая диагональная подсветка (как низкое солнце) ---
warm = Image.new("RGB", (BW, BH), (255, 214, 150))
warm_mask = Image.new("L", (BW, BH), 0)
wdraw = ImageDraw.Draw(warm_mask)
for y in range(BH):
    for_x_t = 0  # placeholder to keep loop structure simple
    pass
# быстрее: построим маску одним линейным градиентом по диагонали через resize
grad = Image.new("L", (2, 2), 0)
grad.putpixel((0, 0), 70)
grad.putpixel((1, 0), 10)
grad.putpixel((0, 1), 40)
grad.putpixel((1, 1), 0)
warm_mask = grad.resize((BW, BH), Image.BICUBIC)
img = Image.composite(warm, img, warm_mask.point(lambda p: int(p * 0.35)))

# --- размытие верхней части (боке заднего плана) ---
blurred = img.filter(ImageFilter.GaussianBlur(radius=10 * SCALE))
mask = Image.new("L", (BW, BH), 0)
mdraw = ImageDraw.Draw(mask)
for y in range(BH):
    t = y / BH
    alpha = max(0, 1 - t / 0.38) ** 1.5
    mdraw.line([(0, y), (BW, y)], fill=int(255 * alpha))
img = Image.composite(blurred, img, mask)

# --- боке-блики (мягкие светлые пятна в размытой зоне — как блики света) ---
bokeh = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
bdraw = ImageDraw.Draw(bokeh)
for _ in range(14):
    bx = random.uniform(0, BW)
    by = random.uniform(0, BH * 0.3)
    r = random.uniform(6, 16) * SCALE
    alpha = random.randint(35, 90)
    col = random.choice([(255, 244, 214, alpha), (214, 255, 210, alpha), (255, 255, 255, alpha)])
    bdraw.ellipse([bx - r, by - r, bx + r, by + r], fill=col)
bokeh = bokeh.filter(ImageFilter.GaussianBlur(radius=7 * SCALE))
img = Image.alpha_composite(img.convert("RGBA"), bokeh).convert("RGB")

# --- виньетка сверху ---
vign = Image.new("L", (BW, BH), 0)
vdraw = ImageDraw.Draw(vign)
for y in range(BH):
    t = y / BH
    alpha = max(0, 1 - t / 0.32) * 95
    vdraw.line([(0, y), (BW, y)], fill=int(alpha))
dark = Image.new("RGB", (BW, BH), (9, 15, 10))
img = Image.composite(dark, img, vign)

# --- белая линия разметки внизу ---
line_y = int(BH * 0.93)
glow = Image.new("L", (BW, BH), 0)
gdraw = ImageDraw.Draw(glow)
gdraw.rectangle([0, line_y - 3 * SCALE, BW, line_y + 3 * SCALE], fill=255)
glow = glow.filter(ImageFilter.GaussianBlur(radius=4 * SCALE))
white = Image.new("RGB", (BW, BH), (232, 238, 226))
img = Image.composite(white, img, glow.point(lambda p: int(p * 0.5)))
draw = ImageDraw.Draw(img)
draw.rectangle([0, line_y - int(0.6 * SCALE), BW, line_y + int(0.6 * SCALE)], fill=(222, 230, 214))

# --- финальный даунскейл + резкость переднего плана + коррекция цвета ---
img = img.resize((W, H), Image.LANCZOS)
sharp = img.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
# резкость применяем только к нижним 65% (передний план), верх остаётся мягким
sharp_mask = Image.new("L", (W, H), 0)
sdraw = ImageDraw.Draw(sharp_mask)
for y in range(H):
    t = y / H
    a = max(0, min(255, int((t - 0.32) / 0.15 * 255)))
    sdraw.line([(0, y), (W, y)], fill=a)
img = Image.composite(sharp, img, sharp_mask)

img = ImageEnhance.Contrast(img).enhance(1.08)
img = ImageEnhance.Color(img).enhance(0.95)
img = ImageEnhance.Brightness(img).enhance(1.02)

out = "grass-photo-v2.jpg"
img.save(out, quality=85, optimize=True)
import os
print(out, os.path.getsize(out), "bytes")
