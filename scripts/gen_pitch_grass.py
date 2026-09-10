"""
Генерирует apps/frontend/static/frontend/img/pitch-grass.svg — процедурную
текстуру травинок для полосы-"газона" за шапкой/заголовком (.pitch-banner,
см. style.css). Настоящей фотографии нет (пользователь прислал референс
картинкой в чат, файла на диске не дал), поэтому вместо плоских CSS-полос —
тысячи тонких травинок разного оттенка/угла/длины, сгруппированные по цвету
в отдельные <path> (не по одному <line> на травинку — иначе файл распухнет).
Скрипт одноразовый (не часть рантайма) — запускается вручную при желании
пересоздать текстуру с другим сидом/плотностью.
"""

import random

random.seed(42)

WIDTH, HEIGHT = 420, 170
N_BLADES = 2600

# Оттенки травы тёмно-зелёные (не --lime — он слишком яркий, убил бы
# контраст белого текста поверх), от тёмного к чуть светлому — для глубины.
COLORS = [
    "#1c3322",
    "#24402c",
    "#2c4a33",
    "#355639",
    "#3f6242",
    "#4a6f48",
]

buckets = {c: [] for c in COLORS}

for _ in range(N_BLADES):
    x = random.uniform(0, WIDTH)
    y = random.uniform(0, HEIGHT)
    length = random.uniform(4, 15)
    angle = random.uniform(75, 105)  # почти вертикально, лёгкий разброс
    import math

    rad = math.radians(angle)
    dx = length * math.cos(rad)
    dy = -length * math.sin(rad)
    color = random.choice(COLORS)
    buckets[color].append(f"M{x:.1f},{y:.1f} l{dx:.1f},{dy:.1f}")

paths = []
for i, color in enumerate(COLORS):
    stroke_width = 0.55 + i * 0.08
    d = " ".join(buckets[color])
    paths.append(
        f'<path d="{d}" stroke="{color}" stroke-width="{stroke_width}" '
        f'stroke-linecap="round" fill="none"/>'
    )

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" preserveAspectRatio="xMidYMax slice">
  <defs>
    <linearGradient id="base" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#14261a"/>
      <stop offset="55%" stop-color="#1f3a26"/>
      <stop offset="100%" stop-color="#28472f"/>
    </linearGradient>
  </defs>
  <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#base)"/>
  {''.join(paths)}
</svg>'''

out_path = "apps/frontend/static/frontend/img/pitch-grass.svg"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(svg)

print(f"written {out_path}, {len(svg)} bytes, {N_BLADES} blades")
