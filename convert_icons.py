import os
import subprocess
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QGuiApplication, QImage
import sys

app = QGuiApplication(sys.argv)
base_dir = os.path.dirname(os.path.abspath(__file__))
base_img = QImage(os.path.join(base_dir, "icon_master_1024.png"))

# 1. Salvar icon.png padrão
base_img.scaled(256, 256, Qt.KeepAspectRatio, Qt.SmoothTransformation).save(
    os.path.join(base_dir, "icon.png"), "PNG"
)

# 2. Gerar iconset para macOS
iconset_dir = os.path.join(base_dir, "TwitchBot.iconset")
os.makedirs(iconset_dir, exist_ok=True)

sizes = [
    (16, "icon_16x16.png"),
    (32, "icon_16x16@2x.png"),
    (32, "icon_32x32.png"),
    (64, "icon_32x32@2x.png"),
    (128, "icon_128x128.png"),
    (256, "icon_128x128@2x.png"),
    (256, "icon_256x256.png"),
    (512, "icon_256x256@2x.png"),
    (512, "icon_512x512.png"),
    (1024, "icon_512x512@2x.png"),
]

for sz, name in sizes:
    scaled = base_img.scaled(sz, sz, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    scaled.save(os.path.join(iconset_dir, name), "PNG")

# 3. Compilar icon.icns com iconutil (macOS only)
if sys.platform == "darwin":
    subprocess.run([
        "iconutil", "-c", "icns", iconset_dir,
        "-o", os.path.join(base_dir, "icon.icns")
    ], check=True)
    print("Gerado icon.icns com sucesso!")

# 4. Salvar icon.ico multi-resolução
ico_path = os.path.join(base_dir, "icon.ico")
base_img.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation).save(ico_path, "ICO")
if not os.path.exists(ico_path) or os.path.getsize(ico_path) == 0:
    base_img.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation).save(ico_path)
print("Gerado icon.ico com sucesso!")
