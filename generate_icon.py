import os
import sys
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import (
    QGuiApplication, QImage, QPainter, QColor, QLinearGradient, QRadialGradient,
    QPainterPath, QPen, QBrush, QFont
)

def create_icon():
    app = QGuiApplication(sys.argv)
    size = 1024
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)

    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)

    # 1. Base Squircle macOS style (cantos arredondados padrão Apple 224px)
    margin = 40
    rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    
    # Sombra suave sob o squircle
    shadow_path = QPainterPath()
    shadow_path.addRoundedRect(rect.translated(0, 15), 210, 210)
    p.fillPath(shadow_path, QColor(0, 0, 0, 90))

    # Fundo do Squircle (Gradiente roxo escuro Twitch espacial)
    bg_path = QPainterPath()
    bg_path.addRoundedRect(rect, 210, 210)

    bg_grad = QLinearGradient(0, 0, size, size)
    bg_grad.setColorAt(0.0, QColor("#140d24"))
    bg_grad.setColorAt(0.5, QColor("#0d0b14"))
    bg_grad.setColorAt(1.0, QColor("#08070c"))
    p.fillPath(bg_path, bg_grad)

    # Borda sutil de neon roxo metálico
    border_pen = QPen(QColor("#772ce8"), 8)
    p.strokePath(bg_path, border_pen)

    # Brilho radial de fundo (Glow central da Twitch)
    glow_grad = QRadialGradient(512, 512, 450)
    glow_grad.setColorAt(0.0, QColor(145, 70, 255, 70))
    glow_grad.setColorAt(0.7, QColor(119, 44, 232, 25))
    glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
    p.fillPath(bg_path, glow_grad)

    # Grade de circuitos sutil no fundo
    circuit_pen = QPen(QColor(145, 70, 255, 30), 2)
    p.setPen(circuit_pen)
    for x in range(120, 920, 80):
        p.drawLine(x, 150, x, 870)
    for y in range(150, 880, 80):
        p.drawLine(120, y, 900, y)

    # Ajuste de centralização vertical (sem o badge de texto)
    y_off = 45

    # 2. Mini-bots / Drones laterais (representando a rede de Viewers)
    def draw_mini_bot(cx, cy, scale=0.45):
        p.save()
        p.translate(cx, cy)
        p.scale(scale, scale)
        
        # Glow do mini-bot
        m_glow = QRadialGradient(0, 0, 180)
        m_glow.setColorAt(0.0, QColor(0, 240, 255, 70))
        m_glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(m_glow)
        p.setPen(Qt.NoPen)
        p.drawEllipse(-180, -180, 360, 360)

        # Cabeça do mini-bot
        m_path = QPainterPath()
        m_path.addRoundedRect(-120, -100, 240, 200, 50, 50)
        m_grad = QLinearGradient(-100, -100, 100, 100)
        m_grad.setColorAt(0.0, QColor("#5c16c5"))
        m_grad.setColorAt(1.0, QColor("#220c4a"))
        p.fillPath(m_path, m_grad)
        p.strokePath(m_path, QPen(QColor("#a970ff"), 4))

        # Visor ciano
        v_path = QPainterPath()
        v_path.addRoundedRect(-85, -45, 170, 90, 30, 30)
        p.fillPath(v_path, QColor("#00F0FF"))

        # Olhos robô (dois pontos)
        p.setBrush(QColor("#ffffff"))
        p.drawRoundedRect(-55, -20, 35, 40, 8, 8)
        p.drawRoundedRect(20, -20, 35, 40, 8, 8)
        p.restore()

    # Desenha 2 mini-bots flutuando ao fundo (Viewers)
    draw_mini_bot(245, 365 + y_off, 0.44)
    draw_mini_bot(779, 365 + y_off, 0.44)

    # 3. Headset Gamer (Aro superior)
    headset_band = QPainterPath()
    headset_band.arcMoveTo(260, 190 + y_off, 504, 504, 25)
    headset_band.arcTo(260, 190 + y_off, 504, 504, 25, 130)
    band_pen = QPen(QColor("#1f1f28"), 48, Qt.SolidLine, Qt.RoundCap)
    p.strokePath(headset_band, band_pen)

    # Fita neon no headset
    neon_band_pen = QPen(QColor("#00F0FF"), 12, Qt.SolidLine, Qt.RoundCap)
    p.strokePath(headset_band, neon_band_pen)

    # 4. Antena do Robô Central (Twitch AI)
    p.setPen(QPen(QColor("#3f3f50"), 16, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(512, 330 + y_off, 512, 230 + y_off)
    # Esfera da antena com pulso de sinal
    ant_glow = QRadialGradient(512, 215 + y_off, 60)
    ant_glow.setColorAt(0.0, QColor("#00F0FF"))
    ant_glow.setColorAt(0.5, QColor(0, 240, 255, 120))
    ant_glow.setColorAt(1.0, QColor(0, 240, 255, 0))
    p.setPen(Qt.NoPen)
    p.setBrush(ant_glow)
    p.drawEllipse(512 - 50, 215 + y_off - 50, 100, 100)
    p.setBrush(QColor("#ffffff"))
    p.drawEllipse(512 - 20, 215 + y_off - 20, 40, 40)

    # 5. Cabeça Principal do Robô (Estilo Twitch Glitch Chat Box)
    robot_head = QPainterPath()
    rw, rh = 470, 390
    rx, ry = 512 - rw / 2, 320 + y_off
    
    robot_head.moveTo(rx + 60, ry)
    robot_head.lineTo(rx + rw - 60, ry)
    robot_head.quadTo(rx + rw, ry, rx + rw, ry + 60)
    robot_head.lineTo(rx + rw, ry + rh - 60)
    robot_head.quadTo(rx + rw, ry + rh, rx + rw - 60, ry + rh)
    # Detalhe do bico estilo Twitch na base
    robot_head.lineTo(rx + 160, ry + rh)
    robot_head.lineTo(rx + 100, ry + rh + 65) # bico do balão
    robot_head.lineTo(rx + 100, ry + rh)
    robot_head.lineTo(rx + 60, ry + rh)
    robot_head.quadTo(rx, ry + rh, rx, ry + rh - 60)
    robot_head.lineTo(rx, ry + 60)
    robot_head.quadTo(rx, ry, rx + 60, ry)
    robot_head.closeSubpath()

    # Sombra da cabeça
    head_shadow = QPainterPath()
    head_shadow.addPath(robot_head)
    p.fillPath(head_shadow.translated(0, 22), QColor(0, 0, 0, 140))

    # Gradiente da carcaça do robô (Twitch Purple premium metálico)
    robot_grad = QLinearGradient(rx, ry, rx + rw, ry + rh)
    robot_grad.setColorAt(0.0, QColor("#a970ff"))
    robot_grad.setColorAt(0.3, QColor("#9146FF"))
    robot_grad.setColorAt(0.8, QColor("#772CE8"))
    robot_grad.setColorAt(1.0, QColor("#451093"))
    p.fillPath(robot_head, robot_grad)

    # Contorno metálico da carcaça
    p.strokePath(robot_head, QPen(QColor("#c5a0ff"), 10))

    # 6. Earpads do Headset (Esquerda e Direita)
    def draw_earpad(ex, ey):
        ep_path = QPainterPath()
        ep_path.addRoundedRect(ex, ey, 70, 180, 30, 30)
        ep_grad = QLinearGradient(ex, ey, ex + 70, ey + 180)
        ep_grad.setColorAt(0.0, QColor("#26262c"))
        ep_grad.setColorAt(0.6, QColor("#18181b"))
        ep_grad.setColorAt(1.0, QColor("#0e0e10"))
        p.fillPath(ep_path, ep_grad)
        p.strokePath(ep_path, QPen(QColor("#00F0FF"), 6))

        # Luz LED circular central no earpad
        led_grad = QRadialGradient(ex + 35, ey + 90, 25)
        led_grad.setColorAt(0.0, QColor("#00F0FF"))
        led_grad.setColorAt(0.8, QColor(0, 240, 255, 60))
        led_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(led_grad)
        p.setPen(Qt.NoPen)
        p.drawEllipse(int(ex + 10), int(ey + 65), 50, 50)

    draw_earpad(rx - 55, ry + 105)
    draw_earpad(rx + rw - 15, ry + 105)

    # 7. Visor Facial do Robô (Tela digital escura com HUD)
    visor_path = QPainterPath()
    vx, vy, vw, vh = rx + 40, ry + 60, rw - 80, 215
    visor_path.addRoundedRect(vx, vy, vw, vh, 40, 40)

    visor_grad = QLinearGradient(vx, vy, vx, vy + vh)
    visor_grad.setColorAt(0.0, QColor("#090810"))
    visor_grad.setColorAt(0.5, QColor("#0d0b18"))
    visor_grad.setColorAt(1.0, QColor("#05040a"))
    p.fillPath(visor_path, visor_grad)
    p.strokePath(visor_path, QPen(QColor("#33185c"), 6))

    # Linhas de varredura digital no visor (Scanlines futuristas)
    p.setPen(QPen(QColor(0, 240, 255, 18), 1))
    for sy in range(int(vy + 10), int(vy + vh - 10), 10):
        p.drawLine(int(vx + 15), sy, int(vx + vw - 15), sy)

    # 8. Olhos Digitais Estilo Twitch (Cápsulas verticais neon ciano com núcleo branco)
    eye_w, eye_h = 58, 115
    eye_y = vy + 50
    left_x = 512 - 98
    right_x = 512 + 40

    def draw_digital_eye(ox):
        # Glow do olho
        eglow = QRadialGradient(ox + eye_w/2, eye_y + eye_h/2, 95)
        eglow.setColorAt(0.0, QColor(0, 240, 255, 210))
        eglow.setColorAt(0.5, QColor(0, 240, 255, 75))
        eglow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(eglow)
        p.setPen(Qt.NoPen)
        p.drawEllipse(int(ox - 30), int(eye_y - 20), eye_w + 60, eye_h + 40)

        # Barra do olho
        ep = QPainterPath()
        ep.addRoundedRect(ox, eye_y, eye_w, eye_h, 16, 16)
        
        # Gradiente ciano elétrico
        e_grad = QLinearGradient(ox, eye_y, ox + eye_w, eye_y + eye_h)
        e_grad.setColorAt(0.0, QColor("#ffffff"))
        e_grad.setColorAt(0.4, QColor("#70ffff"))
        e_grad.setColorAt(1.0, QColor("#00c8e0"))
        p.fillPath(ep, e_grad)

        # Núcleo branco intenso (pupila cibernética)
        p.setBrush(QColor(255, 255, 255, 240))
        p.drawRoundedRect(int(ox + 12), int(eye_y + 18), eye_w - 24, eye_h - 36, 8, 8)

    draw_digital_eye(left_x)
    draw_digital_eye(right_x)

    # Finalizar pintura
    p.end()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(base_dir, "icon_master_1024.png")
    img.save(out_path, "PNG")
    print(f"Ícone limpo gerado com sucesso em: {out_path}")

if __name__ == "__main__":
    create_icon()
