"""
生成应用图标

创建 ScreenRecorder 的 .ico 图标文件，用于：
- 窗口标题栏图标
- .exe 可执行文件图标
- 桌面快捷方式图标
"""

from PIL import Image, ImageDraw


def generate_icon(output_path: str = "app_icon.ico"):
    """生成应用图标"""
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 蓝色圆角矩形背景
    draw.rounded_rectangle([8, 8, 248, 248], radius=40, fill=(37, 99, 235, 255))

    # 白色圆形（镜头）
    draw.ellipse([58, 58, 198, 198], fill=(255, 255, 255, 240))

    # 红色录制圆点
    draw.ellipse([98, 98, 158, 158], fill=(239, 68, 68, 255))

    # 保存为 ICO 格式（多尺寸）
    img.save(
        output_path,
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )
    print(f"图标已生成: {output_path}")


if __name__ == "__main__":
    generate_icon()
