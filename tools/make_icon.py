"""生成项目图标(购物车 + 对话气泡,蓝紫渐变背景)

用法: D:/venvs/langchain-project/Scripts/python.exe tools/make_icon.py
输出: assets/app.ico(多尺寸)+ assets/preview.png(预览图)
"""
from pathlib import Path

from PIL import Image, ImageDraw

OUT_DIR = Path(__file__).resolve().parent.parent / "assets"
OUT_DIR.mkdir(exist_ok=True)

S = 1024  # 先在 1024 大画布上画,缩小时更细腻
TOP = (102, 126, 234)     # 蓝 #667eea(和登录页渐变同色系)
BOTTOM = (118, 75, 162)   # 紫 #764ba2
WHITE = (255, 255, 255, 255)


def make_icon(size=S) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # 1) 蓝紫渐变背景
    grad = Image.new("RGB", (size, size))
    gd = ImageDraw.Draw(grad)
    for y in range(size):
        t = y / size
        color = tuple(int(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3))
        gd.line([(0, y), (size, y)], fill=color)

    # 2) 圆角方形遮罩(Windows 图标惯例的圆角)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, size - 1, size - 1], radius=int(size * 0.22), fill=255
    )
    img.paste(grad, (0, 0), mask)

    d = ImageDraw.Draw(img)
    k = size / 1024  # 画布缩放系数
    w = int(46 * k)  # 线宽

    # 3) 购物车(白色线条)
    # 手柄:一小段横线 + 斜线接车斗
    d.line([(120 * k, 300 * k), (222 * k, 300 * k), (300 * k, 470 * k)],
           fill=WHITE, width=w, joint="curve")
    # 车斗:上宽下窄的梯形
    d.line([(300 * k, 470 * k), (760 * k, 470 * k), (660 * k, 700 * k),
            (370 * k, 700 * k), (300 * k, 470 * k)],
           fill=WHITE, width=w, joint="curve")
    # 两个轮子
    r = 52 * k
    d.ellipse([400 * k - r, 790 * k - r, 400 * k + r, 790 * k + r], fill=WHITE)
    d.ellipse([620 * k - r, 790 * k - r, 620 * k + r, 790 * k + r], fill=WHITE)

    # 4) 对话气泡(右上角,带三个小点 = "在回答")
    d.rounded_rectangle([600 * k, 150 * k, 920 * k, 350 * k],
                        radius=int(60 * k), fill=WHITE)
    # 气泡的小尾巴
    d.polygon([(700 * k, 340 * k), (700 * k, 440 * k), (790 * k, 345 * k)], fill=WHITE)
    # 三个点
    dot_r = 22 * k
    for cx in (680, 760, 840):
        d.ellipse([cx * k - dot_r, 250 * k - dot_r, cx * k + dot_r, 250 * k + dot_r],
                  fill=BOTTOM)
    return img


def main():
    img = make_icon()
    # 导出 Windows 图标需要的各个尺寸
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    img.save(OUT_DIR / "app.ico", format="ICO", sizes=sizes)
    img.resize((256, 256), Image.LANCZOS).save(OUT_DIR / "preview.png")
    print("图标已生成:", OUT_DIR / "app.ico")


if __name__ == "__main__":
    main()
