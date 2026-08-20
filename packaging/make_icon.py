"""生成应用图标：packaging/assets/app.ico（Windows）+ app.icns（macOS）。

主题：深蓝雷达（卫星信号扫描），呼应 GNSS 文献调研。
用法：python packaging/make_icon.py
依赖：Pillow；macOS 生成 icns 还需系统自带 iconutil。
"""
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "packaging" / "assets"

SIZE = 1024
BLUE_DARK = (11, 42, 91, 255)
BLUE_ACCENT = (26, 109, 240, 255)
WHITE = (255, 255, 255, 255)


def draw_icon() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = cy = SIZE // 2

    # 圆形深蓝底
    d.ellipse([40, 40, SIZE - 40, SIZE - 40], fill=BLUE_DARK)
    # 外圈高亮描边
    d.ellipse([40, 40, SIZE - 40, SIZE - 40], outline=BLUE_ACCENT, width=10)

    # 雷达波纹（三条白色弧线，左上开口）
    for radius, width in ((180, 26), (330, 26), (480, 26)):
        d.arc([cx - radius, cy - radius, cx + radius, cy + radius],
              start=135, end=400, fill=WHITE, width=width)

    # 扫描线（中心向右上）
    import math
    angle = math.radians(45)
    x2 = cx + int(430 * math.cos(angle))
    y2 = cy - int(430 * math.sin(angle))
    d.line([cx, cy, x2, y2], fill=WHITE, width=22)

    # 中心信号点（白底 + 蓝色小点）
    d.ellipse([cx - 70, cy - 70, cx + 70, cy + 70], fill=WHITE)
    d.ellipse([cx - 30, cy - 30, cx + 30, cy + 30], fill=BLUE_ACCENT)
    return img


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    img = draw_icon()

    # PNG（mac 预览 / 备用）
    img.save(ASSETS / "app.png")
    print("已生成 app.png")

    # Windows .ico（多尺寸）
    img.save(ASSETS / "app.ico", format="ICO",
             sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
                    (128, 128), (256, 256)])
    print("已生成 app.ico")

    # macOS .icns（经 iconset + iconutil）
    if sys.platform == "darwin":
        iconset = ASSETS / "AppIcon.iconset"
        iconset.mkdir(exist_ok=True)
        for s in (16, 32, 128, 256, 512):
            img.resize((s, s), Image.LANCZOS).save(iconset / f"icon_{s}x{s}.png")
            img.resize((s * 2, s * 2), Image.LANCZOS).save(iconset / f"icon_{s}x{s}@2x.png")
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(ASSETS / "app.icns")],
            check=True)
        print("已生成 app.icns")
    else:
        print("非 macOS 环境，跳过 icns（在 Mac 上构建 .app 时自动生成）")


if __name__ == "__main__":
    main()
