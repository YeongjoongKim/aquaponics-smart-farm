import sys
import requests
import time
from threading import Thread

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QFrame, QGridLayout, QSizePolicy)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QBrush, QPainterPath

# 그래프용
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# --- 설정 ---
API_URL = "http://localhost:5000/api/current"
REFRESH_RATE = 1000  # 1초

# --- 디자인 색상 (다크 모드) ---
COLOR_BG = "#1a1c24"
COLOR_CARD = "#252836"
COLOR_TEXT = "#e0e0e0"
COLOR_TEXT_DIM = "#b0b3b8"
COLOR_GREEN = "#00e676"
COLOR_RED = "#ff1744"
COLOR_BLUE = "#2979ff"

# ==========================================
# 1. 데이터 가져오는 워커 스레드
# ==========================================
class DataWorker(QThread):
    data_signal = Signal(dict)

    def run(self):
        while True:
            try:
                response = requests.get(API_URL, timeout=1)
                if response.status_code == 200:
                    data = response.json().get("readings", {})
                    self.data_signal.emit(data)
            except:
                pass 
            time.sleep(1)

# ==========================================
# 2. 커스텀 게이지 위젯 (수정됨: 텍스트 위치 조정)
# ==========================================
class GaugeWidget(QWidget):
    def __init__(self, title, unit, min_val, max_val, safe_min, safe_max):
        super().__init__()
        self.title = title
        self.unit = unit
        self.min_val = min_val
        self.max_val = max_val
        self.safe_min = safe_min
        self.safe_max = safe_max
        self.value = 0
        self.setMinimumSize(180, 180) # 크기 약간 키움

    def update_value(self, value):
        self.value = value
        self.update() 

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 좌표 설정
        width = self.width()
        height = self.height()
        side = min(width, height)
        # 게이지가 그려질 사각형 영역
        rect = QRectF((width - side) / 2 + 10, (height - side) / 2 + 10, side - 20, side - 20)

        # 1. 배경 아크 (회색)
        pen = QPen(QColor("#383b47"), 12, Qt.SolidLine, Qt.RoundCap) # 두께 12로 증가
        painter.setPen(pen)
        # 시작각도 -225도 (6시 방향 기준 왼쪽), 스팬 270도
        start_angle = 225 * 16
        span_angle = -270 * 16
        painter.drawArc(rect, start_angle, span_angle)

        # 2. 값 아크 (색상)
        is_safe = self.safe_min <= self.value <= self.safe_max
        color = QColor(COLOR_GREEN) if is_safe else QColor(COLOR_RED)
        
        # 값 비율 계산
        ratio = (self.value - self.min_val) / (self.max_val - self.min_val)
        ratio = max(0.0, min(1.0, ratio))
        value_span = int(-270 * ratio * 16)

        pen.setColor(color)
        painter.setPen(pen)
        painter.drawArc(rect, start_angle, value_span)

        # 3. 텍스트 그리기
        painter.setPen(QColor(COLOR_TEXT))
        
        # [수정] 수치 (중앙)
        painter.setFont(QFont("Arial", 24, QFont.Bold))
        text_rect = QRectF(rect.left(), rect.top(), rect.width(), rect.height() - 20) # 약간 위로 올림
        painter.drawText(text_rect, Qt.AlignCenter, f"{self.value:.1f}")

        # [수정] 단위 (수치 바로 아래)
        painter.setPen(QColor(COLOR_TEXT_DIM))
        painter.setFont(QFont("Arial", 11))
        unit_rect = QRectF(rect.left(), rect.center().y() + 15, rect.width(), 30)
        painter.drawText(unit_rect, Qt.AlignCenter, self.unit)

        # [수정] 항목 이름 (맨 아래쪽 - 게이지가 열려있는 공간)
        painter.setPen(QColor(COLOR_TEXT))
        painter.setFont(QFont("Malgun Gothic", 12, QFont.Bold))
        # 사각형의 바닥 부분에 배치
        title_rect = QRectF(rect.left(), rect.bottom() - 35, rect.width(), 30)
        painter.drawText(title_rect, Qt.AlignCenter, self.title)


# ==========================================
# 3. 스마트 카드 위젯
# ==========================================
class MetricCard(QFrame):
    def __init__(self, title, unit):
        super().__init__()
        self.unit = unit
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_CARD};
                border-radius: 12px;
                border: 1px solid #3f4354;
            }}
        """)
        self.setFrameShape(QFrame.StyledPanel)
        
        layout = QVBoxLayout(self)
        
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet(f"color: {COLOR_TEXT_DIM}; font-weight: bold; font-family: 'Malgun Gothic';")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        
        self.lbl_value = QLabel("-")
        self.lbl_value.setStyleSheet(f"color: {COLOR_TEXT}; font-size: 24px; font-weight: bold;")
        self.lbl_value.setAlignment(Qt.AlignCenter)

        self.lbl_status = QLabel("대기 중")
        self.lbl_status.setStyleSheet(f"background-color: #383b47; color: white; border-radius: 10px; padding: 4px;")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setFixedHeight(25)

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_value)
        layout.addWidget(self.lbl_status)
    
    def update_data(self, value, safe_min, safe_max):
        try:
            val_float = float(value)
        except:
            val_float = 0.0

        is_safe = safe_min <= val_float <= safe_max
        
        if isinstance(value, float):
            self.lbl_value.setText(f"{value:.1f} {self.unit}")
        else:
            self.lbl_value.setText(f"{value} {self.unit}")

        if is_safe:
            color = COLOR_GREEN
            bg_color = "rgba(0, 230, 118, 0.15)"
            msg = "정상"
        else:
            color = COLOR_RED
            bg_color = "rgba(255, 23, 68, 0.15)"
            msg = "주의"

        self.lbl_value.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold;")
        self.lbl_status.setText(msg)
        self.lbl_status.setStyleSheet(f"background-color: {bg_color}; color: {color}; border-radius: 5px;")

# ==========================================
# 4. 메인 윈도우
# ==========================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("아쿠아포닉스 스마트팜 모니터링 (PySide6)")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet(f"background-color: {COLOR_BG};")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("🌿 아쿠아포닉스 스마트팜 모니터링")
        title.setStyleSheet(f"color: {COLOR_TEXT}; font-size: 24px; font-weight: bold; font-family: 'Malgun Gothic';")
        main_layout.addWidget(title)

        # --- Zone A ---
        group_a = QFrame()
        layout_a = QHBoxLayout(group_a)
        
        self.gauge_temp = GaugeWidget("수온", "°C", 0, 50, 18, 28)
        self.gauge_level = GaugeWidget("수위", "%", 0, 100, 60, 100)
        self.gauge_ph = GaugeWidget("pH", "", 0, 14, 5.5, 7.5)
        self.gauge_turb = GaugeWidget("탁도", "NTU", 0, 100, 0, 50)

        layout_a.addWidget(self.gauge_temp)
        layout_a.addWidget(self.gauge_level)
        layout_a.addWidget(self.gauge_ph)
        layout_a.addWidget(self.gauge_turb)
        
        main_layout.addWidget(QLabel("💧 Zone A: 정수 탱크 (Clean Water)", styleSheet=f"color:{COLOR_TEXT}; font-weight:bold;"))
        main_layout.addWidget(group_a)

        # --- Zone B & C ---
        mid_layout = QHBoxLayout()
        main_layout.addLayout(mid_layout)

        # Zone B
        zone_b_layout = QVBoxLayout()
        mid_layout.addLayout(zone_b_layout, stretch=1)
        
        zone_b_label = QLabel("🧪 Zone B: 배양액 탱크")
        zone_b_label.setStyleSheet(f"color:{COLOR_TEXT}; font-weight:bold;")
        zone_b_layout.addWidget(zone_b_label)

        grid_b = QGridLayout()
        zone_b_layout.addLayout(grid_b)

        self.card_ph = MetricCard("pH 농도", "")
        self.card_ec = MetricCard("EC 전도도", "μS")
        self.card_do = MetricCard("용존산소량", "mg/L")
        self.card_temp = MetricCard("수온", "°C")
        self.card_level = MetricCard("현재 수위", "%")

        grid_b.addWidget(self.card_ph, 0, 0)
        grid_b.addWidget(self.card_ec, 0, 1)
        grid_b.addWidget(self.card_do, 1, 0)
        grid_b.addWidget(self.card_temp, 1, 1)
        grid_b.addWidget(self.card_level, 2, 0, 1, 2)

        # Zone C
        zone_c_layout = QVBoxLayout()
        mid_layout.addLayout(zone_c_layout, stretch=2)

        zone_c_label = QLabel("📉 Zone C: 식물 배양 라인 (EC 변화)")
        zone_c_label.setStyleSheet(f"color:{COLOR_TEXT}; font-weight:bold;")
        zone_c_layout.addWidget(zone_c_label)

        plt.style.use('dark_background')
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.fig.patch.set_facecolor(COLOR_CARD)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setStyleSheet(f"background-color: {COLOR_CARD}; border-radius: 12px;")
        
        graph_frame = QFrame()
        graph_frame.setStyleSheet(f"background-color: {COLOR_CARD}; border-radius: 12px; border: 1px solid #3f4354;")
        graph_layout = QVBoxLayout(graph_frame)
        graph_layout.addWidget(self.canvas)
        
        zone_c_layout.addWidget(graph_frame)

        self.worker = DataWorker()
        self.worker.data_signal.connect(self.update_ui)
        self.worker.start()

    def update_ui(self, data):
        self.gauge_temp.update_value(data.get('temperature', 0))
        self.gauge_level.update_value(data.get('water_level', 0))
        self.gauge_ph.update_value(data.get('pH', 0))
        self.gauge_turb.update_value(data.get('turbidity', 0))

        self.card_ph.update_data(data.get('pH', 0), 5.5, 7.5)
        self.card_ec.update_data(data.get('EC', 0), 1000, 1600)
        self.card_do.update_data(data.get('DO', 0), 5.0, 20.0)
        self.card_temp.update_data(data.get('temperature', 0), 18, 28)
        self.card_level.update_data(data.get('water_level', 0), 60, 100)

        self.ax.clear()
        self.ax.set_facecolor(COLOR_CARD)
        
        ec_val = data.get('EC', 0)
        x = ['Start', 'Mid', 'End']
        y = [ec_val, ec_val * 0.96, ec_val * 0.90]

        self.ax.plot(x, y, marker='o', color=COLOR_BLUE, linewidth=3, markersize=8)
        self.ax.fill_between(x, y, alpha=0.2, color=COLOR_BLUE)
        
        self.ax.grid(True, color='#3f4354', linestyle='--')
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['bottom'].set_color('#b0b3b8')
        self.ax.spines['left'].set_color('#b0b3b8')
        self.ax.tick_params(colors='#b0b3b8')
        
        self.canvas.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())