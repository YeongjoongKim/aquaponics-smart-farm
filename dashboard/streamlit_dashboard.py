import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import time
import uuid

# --- 설정 ---
API_URL = "http://localhost:5001/api/current"
st.set_page_config(
    page_title="아쿠아포닉스 스마트팜",
    page_icon="🌿",
    layout="wide"
)

# --- CSS 스타일 (다크 모드) ---
st.markdown("""
    <style>
    /* 1. 전체 배경: 깊은 짙은 남색 */
    .stApp {
        background-color: #1a1c24;
    }
    
    /* 2. 제목 등 일반 텍스트 색상 변경 (흰색) */
    h1, h2, h3, p, div, span {
        color: #e0e0e0;
    }
    
    /* 3. 카드 스타일 */
    div.css-card {
        background-color: #252836; 
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #3f4354;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        margin-bottom: 10px;
        text-align: center;
    }
    div.css-card-label {
        color: #b0b3b8;
        font-size: 14px;
        font-weight: 700;
        margin-bottom: 5px;
    }
    div.css-card-value {
        font-size: 28px;
        font-weight: 800;
    }
    div.css-card-unit {
        font-size: 16px;
        font-weight: 500;
        color: #6c757d;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🌿 아쿠아포닉스 스마트팜 모니터링")
st.caption("Real-time Smart Farm Dashboard powered by Streamlit")

# 데이터 가져오기
def get_data():
    try:
        response = requests.get(API_URL, timeout=1)
        if response.status_code == 200:
            return response.json().get("readings", {})
    except:
        return None
    return None

# Zone A용 계기판 (여백 개선)
def create_gauge(label, value, min_val, max_val, safe_min, safe_max, unit):
    color = "#00e676" if safe_min <= value <= safe_max else "#ff1744"
    
    empty_color = "#383b47"
    safe_bg_color = "rgba(0, 230, 118, 0.1)"

    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        number = {'suffix': unit, 'font': {'size': 20, 'color': '#ffffff'}},
        title = {'text': label, 'font': {'size': 15, 'color': "#b0b3b8"}},
        gauge = {
            'axis': {'range': [min_val, max_val], 'tickwidth': 1, 'tickcolor': "#b0b3b8"},
            'bar': {'color': color},
            'bgcolor': "rgba(0,0,0,0)",
            'borderwidth': 0,
            'steps': [
                {'range': [0, safe_min], 'color': empty_color},
                {'range': [safe_min, safe_max], 'color': safe_bg_color}, 
                {'range': [safe_max, max_val], 'color': empty_color}
            ],
            'threshold': {
                'line': {'color': "#ff1744", 'width': 4},
                'thickness': 0.75,
                'value': value
            }
        }
    ))
    # [수정] 위쪽 여백(t)을 30 -> 50으로 늘려 제목과 그래프 사이 공간 확보
    fig.update_layout(height=180, margin=dict(l=20, r=20, t=50, b=10), paper_bgcolor="rgba(0,0,0,0)")
    return fig

# Zone B용 스마트 카드
def metric_card(label, value, unit, safe_min, safe_max):
    try:
        val_float = float(value)
    except ValueError:
        val_float = 0.0

    is_safe = safe_min <= val_float <= safe_max
    
    if is_safe:
        text_color = "#00e676"
        icon = ""
        status_bg = "rgba(0, 230, 118, 0.15)"
        status_text = "정상 (Normal)"
    else:
        text_color = "#ff1744"
        icon = "⚠️"
        status_bg = "rgba(255, 23, 68, 0.15)"
        status_text = "주의 (Warning)"

    html_code = f"""
    <div class="css-card" style="border-bottom: 4px solid {text_color};">
        <div class="css-card-label">{label}</div>
        <div class="css-card-value" style="color: {text_color};">
            {icon} {value} <span class="css-card-unit">{unit}</span>
        </div>
        <div style="margin-top:5px; font-size:12px; color:{text_color}; background-color:{status_bg}; padding:4px 10px; border-radius:12px; display:inline-block; font-weight:bold;">
            {status_text}
        </div>
    </div>
    """
    st.markdown(html_code, unsafe_allow_html=True)

placeholder = st.empty()

while True:
    data = get_data()
    
    if data:
        with placeholder.container():
            # === Zone A ===
            st.subheader("💧 Zone A: 정수 탱크 (Clean Water)")
            
            # [수정] 제목과 그래프 사이에 빈 공간 추가 (줄바꿈)
            st.markdown("<br>", unsafe_allow_html=True)
            
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                fig = create_gauge("수온", data['temperature'], 0, 50, 18, 28, "°C")
                st.plotly_chart(fig, use_container_width=True, key=f"g1_{uuid.uuid4()}")
            with c2:
                fig = create_gauge("수위", data['water_level'], 0, 100, 60, 100, "%")
                st.plotly_chart(fig, use_container_width=True, key=f"g2_{uuid.uuid4()}")
            with c3:
                fig = create_gauge("pH", data['pH'], 0, 14, 5.5, 7.5, "")
                st.plotly_chart(fig, use_container_width=True, key=f"g3_{uuid.uuid4()}")
            with c4:
                fig = create_gauge("탁도", data['turbidity'], 0, 100, 0, 50, "NTU")
                st.plotly_chart(fig, use_container_width=True, key=f"g4_{uuid.uuid4()}")

            st.divider()

            # === Zone B & Zone C ===
            col_b, col_c = st.columns([1, 2])

            with col_b:
                st.subheader("🧪 Zone B: 배양액 탱크")
                st.caption("실시간 수질 측정값")
                
                r1c1, r1c2 = st.columns(2)
                with r1c1:
                    metric_card("pH 농도", f"{data['pH']:.2f}", "", 5.5, 7.5)
                with r1c2:
                    metric_card("전기전도도 (EC)", f"{data['EC']:.0f}", "μS", 1000, 1600)
                
                r2c1, r2c2 = st.columns(2)
                with r2c1:
                    metric_card("용존산소량 (DO)", f"{data['DO']:.1f}", "mg/L", 5.0, 20.0)
                with r2c2:
                    metric_card("수온 (Temp)", f"{data['temperature']:.1f}", "°C", 18, 28)
                
                metric_card("현재 수위", f"{int(data['water_level'])}", "%", 60, 100)

            with col_c:
                st.subheader("📉 Zone C: 식물 배양 라인")
                st.caption("EC 농도 변화 추이")
                
                ec_val = data['EC']
                graph_data = pd.DataFrame({
                    'Stage': ['Start', 'Mid', 'End'],
                    'EC Value': [ec_val, ec_val * 0.96, ec_val * 0.90]
                })
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=graph_data['Stage'], 
                    y=graph_data['EC Value'],
                    mode='lines+markers+text',
                    text=[f"{v:.0f}" for v in graph_data['EC Value']],
                    textposition="top center",
                    line=dict(color='#2979ff', width=4, shape='spline'),
                    marker=dict(size=12, color='#1a1c24', line=dict(width=2, color='#2979ff')),
                    fill='tozeroy',
                    fillcolor='rgba(41, 121, 255, 0.2)'
                ))
                
                fig.update_layout(
                    margin=dict(l=20, r=20, t=40, b=20),
                    height=350,
                    xaxis=dict(
                        showgrid=False, 
                        showline=True, linewidth=1, linecolor='#555',
                        tickfont=dict(color='#e0e0e0')
                    ),
                    yaxis=dict(
                        showgrid=True, gridcolor='#3f4354',
                        showline=True, linewidth=1, linecolor='#555',
                        title="EC (μS/cm)",
                        title_font=dict(color='#e0e0e0'),
                        tickfont=dict(color='#e0e0e0')
                    ),
                    paper_bgcolor="#252836",
                    plot_bgcolor="#252836",
                    shapes=[dict(
                        type='rect', xref='paper', yref='paper',
                        x0=0, y0=0, x1=1, y1=1,
                        line=dict(color='#3f4354', width=1)
                    )]
                )
                st.plotly_chart(fig, use_container_width=True, key=f"chart_{uuid.uuid4()}")

    else:
        with placeholder.container():
            st.error("🚨 서버 연결 실패")
            st.warning("mock_server.py가 5001번 포트에서 실행 중인지 확인해주세요.")
            time.sleep(2)

    time.sleep(1)