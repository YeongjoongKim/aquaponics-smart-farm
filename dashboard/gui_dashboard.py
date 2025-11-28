import tkinter as tk
from tkinter import ttk
import requests
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading

# --- 설정 ---
API_URL = "http://localhost:5001/api/current"  # 시뮬레이션 서버 주소
REFRESH_RATE = 1000  # 1초마다 화면 갱신

class SmartFarmDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("아쿠아포닉스 스마트팜 모니터링 시스템")
        self.root.geometry("1000x700")
        
        # 탭 구조 생성
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=5)
        
        self.monitor_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.monitor_frame, text='모니터링 대시보드')
        
        # UI 레이아웃 배치
        self.create_layout()
        
        # 데이터 자동 갱신 시작
        self.update_data()

    def create_layout(self):
        # 상단 영역 (Zone A, B)
        top_paned = ttk.PanedWindow(self.monitor_frame, orient=tk.HORIZONTAL)
        top_paned.pack(expand=True, fill='both', padx=5, pady=5)

        # === Zone A: 정수 탱크 (녹색 진행바) ===
        self.zone_a = ttk.LabelFrame(top_paned, text="Zone A: 정수 탱크 (Clean Water)")
        top_paned.add(self.zone_a, weight=2)
        
        self.bars = {}
        self.labels_a = {}
        sensors_a = [
            ("수온 (Temp)", "°C", 100), 
            ("수위 (Level)", "%", 100), 
            ("pH 농도", "", 14), 
            ("탁도 (Turbidity)", "NTU", 1000)
        ]
        
        for idx, (name, unit, max_val) in enumerate(sensors_a):
            lbl = ttk.Label(self.zone_a, text=f"{name}", font=("Malgun Gothic", 10))
            lbl.grid(row=idx, column=0, sticky="w", padx=10, pady=10)
            self.labels_a[name] = lbl
            
            # 녹색 스타일 프로그레스바
            style_name = "green.Horizontal.TProgressbar"
            bar = ttk.Progressbar(self.zone_a, length=300, maximum=max_val, mode='determinate', style=style_name)
            bar.grid(row=idx, column=1, padx=10, pady=10)
            self.bars[name] = bar

        # === Zone B: 배양액 탱크 (숫자 박스) ===
        self.zone_b = ttk.LabelFrame(top_paned, text="Zone B: 배양액 탱크 (Nutrient Tank)")
        top_paned.add(self.zone_b, weight=1)

        self.digital_values = {}
        sensors_b = [("pH", "pH"), ("EC", "μS"), ("DO", "mg/L"), ("수온", "°C"), ("수위", "%")]

        for idx, (key, unit) in enumerate(sensors_b):
            ttk.Label(self.zone_b, text=f"{key}:", font=("Malgun Gothic", 10)).grid(row=idx, column=0, sticky="e", padx=10, pady=12)
            val_var = tk.StringVar(value="-")
            # 읽기 전용 박스처럼 보이게 설정
            entry = tk.Entry(self.zone_b, textvariable=val_var, justify="center", font=("Arial", 12, "bold"), bd=2)
            entry.grid(row=idx, column=1, sticky="ew", padx=10, pady=5)
            self.digital_values[key] = val_var

        # === Zone C: 그래프 (Matplotlib) ===
        self.zone_c = ttk.LabelFrame(self.monitor_frame, text="Zone C: 식물 배양 라인 (EC 농도 변화)")
        self.zone_c.pack(expand=True, fill='both', padx=5, pady=5)

        self.fig = Figure(figsize=(5, 3), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.zone_c)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

    def update_data(self):
        """서버에서 데이터를 가져와 화면을 갱신"""
        def fetch():
            try:
                response = requests.get(API_URL, timeout=1)
                if response.status_code == 200:
                    data = response.json().get("readings", {})
                    # UI 갱신은 메인 스레드에서 해야 함
                    self.root.after(0, lambda: self.refresh_ui(data))
            except:
                pass # 연결 실패 시 무시하고 다음 루프
            
            # 다음 갱신 예약
            self.root.after(REFRESH_RATE, self.update_data)

        threading.Thread(target=fetch, daemon=True).start()

    def refresh_ui(self, data):
        """가져온 데이터로 위젯 값 변경"""
        # 데이터 추출
        ph = data.get("pH", 0)
        ec = data.get("EC", 0)
        temp = data.get("temperature", 0)
        level = data.get("water_level", 0)
        turbidity = data.get("turbidity", 0)
        do = data.get("DO", 0)

        # Zone A 갱신
        self.bars["수온 (Temp)"].configure(value=temp)
        self.labels_a["수온 (Temp)"].config(text=f"수온 (Temp): {temp} °C")
        self.bars["수위 (Level)"].configure(value=level)
        self.labels_a["수위 (Level)"].config(text=f"수위 (Level): {level} %")
        self.bars["pH 농도"].configure(value=ph)
        self.labels_a["pH 농도"].config(text=f"pH 농도: {ph:.2f}")
        self.bars["탁도 (Turbidity)"].configure(value=turbidity)
        self.labels_a["탁도 (Turbidity)"].config(text=f"탁도 (Turbidity): {turbidity} NTU")

        # Zone B 갱신
        self.digital_values["pH"].set(f"{ph:.2f}")
        self.digital_values["EC"].set(f"{ec:.1f}")
        self.digital_values["DO"].set(f"{do:.1f}")
        self.digital_values["수온"].set(f"{temp:.1f}")
        self.digital_values["수위"].set(f"{int(level)}")

        # Zone C 그래프 갱신 (시각적 효과용)
        self.ax.clear()
        self.ax.set_title("EC Concentration Drop (Zone C)")
        self.ax.set_ylabel("EC (μS/cm)")
        self.ax.grid(True)
        # 현재 EC 값에서 시작해 농도가 떨어지는 가상의 그래프
        x = ['Start', 'Mid', 'End']
        y = [ec, ec * 0.95, ec * 0.85]
        self.ax.plot(x, y, marker='o', color='blue', linewidth=2)
        self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use('clam')
    style.configure("green.Horizontal.TProgressbar", foreground='green', background='green')
    
    app = SmartFarmDashboard(root)
    root.mainloop()