"""
Плоская 2D-версия газона (в отличие от фото-реалистичной pitch-grass.jpg,
см. gen_pitch_grass_photo.py) — три слоя рваных силуэтов травы плашками
цвета, без шума/размытия/градиентов. Классический flat-illustration приём:
тёмное "небо" (--bg приложения) сверху, зубчатые "заросли" разной высоты
снизу, задний план темнее, передний — светлее/ярче.
Пишет apps/frontend/static/frontend/img/pitch-grass-flat.svg.
"""
import random

random.seed(3)

W, H = 480, 220


def jagged_path(base_y, min_h, max_h, step, jitter, color):
    """Зубчатый силуэт: рваные треугольные "былинки" от base_y вверх."""
    pts = [f"0,{H}"]
    x = -10
    while x <= W + 10:
        peak_h = random.uniform(min_h, max_h)
        px = x + random.uniform(-jitter, jitter)
        pts.append(f"{px:.1f},{base_y - peak_h:.1f}")
        x += step
    pts.append(f"{W + 10},{H}")
    d = "M" + " L".join(pts) + " Z"
    return f'<path d="{d}" fill="{color}"/>'


svg_parts = []
svg_parts.append(f'<rect width="{W}" height="{H}" fill="oklch(0.16 0.014 55)"/>')

# Задний слой — самый тёмный и низкий, задаёт общую линию горизонта.
svg_parts.append(jagged_path(base_y=H * 0.62, min_h=14, max_h=30, step=9, jitter=4, color="#1c3a24"))
# Средний слой — чуть светлее и выше.
svg_parts.append(jagged_path(base_y=H * 0.72, min_h=22, max_h=46, step=11, jitter=5, color="#255030"))
# Передний слой — самый светлый/яркий, самый высокий, ближе к камере.
svg_parts.append(jagged_path(base_y=H * 0.86, min_h=30, max_h=64, step=8, jitter=6, color="#357a41"))

# Белая линия разметки поверх переднего слоя, у самого низа.
svg_parts.append(f'<rect x="0" y="{H - 10}" width="{W}" height="3" fill="oklch(0.95 0.01 90 / 0.55)"/>')

svg = (
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
    f'preserveAspectRatio="xMidYMax slice">' + "".join(svg_parts) + "</svg>"
)

out_path = "apps/frontend/static/frontend/img/pitch-grass-flat.svg"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(svg)

print(f"written {out_path}, {len(svg)} bytes")
