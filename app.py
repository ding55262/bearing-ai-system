# -*- coding: utf-8 -*-
import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from scipy.signal import hilbert
import scipy.io
import io, re, warnings, os, glob
import requests
import json
import time
import sqlite3
import hashlib

# 3D 渲染库
import plotly.graph_objects as go
import trimesh

warnings.filterwarnings("ignore")
plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# ===================== 数据库与安全配置 =====================
DB_FILE = "users.db"

def init_db():
    """初始化数据库，如果不存在则创建一个默认管理员账号"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT)''')
    # 检查是否已有 admin 账号，没有则创建
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        # 默认 admin 密码 123456
        hashed_pw = hashlib.sha256("123456".encode()).hexdigest()
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("admin", hashed_pw))
    conn.commit()
    conn.close()

def add_user(username, password):
    """注册新用户，密码进行 SHA256 加密"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # 用户名已存在
    finally:
        conn.close()

def verify_user(username, password):
    """验证用户登录"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hashed_pw))
    user = c.fetchone()
    conn.close()
    return user is not None

# 初始化数据库
init_db()

# ===================== 读取 Token 配置 =====================
try:
    COZE_API_KEY = st.secrets["COZE_API_KEY"]
    COZE_BOT_ID = st.secrets["COZE_BOT_ID"]
except Exception:
    COZE_API_KEY = "pat_填入你新生成的Token"
    COZE_BOT_ID = "7706858644994179091"

# ===================== 极致工业风 UI 样式注入 =====================
def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
        .stApp {
            background: radial-gradient(circle at 50% -20%, #1e293b 0%, #0f172a 60%, #020617 100%);
            font-family: 'Inter', "SimHei", sans-serif; color: #e2e8f0;
        }
        header { background: transparent !important; }
        h1 { background: -webkit-linear-gradient(45deg, #38bdf8, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800 !important; }
        h2, h3 { color: #f8fafc !important; font-weight: 600 !important; }
        [data-testid="stSidebar"] { background: rgba(15, 23, 42, 0.6) !important; backdrop-filter: blur(20px); border-right: 1px solid rgba(255, 255, 255, 0.05); }
        [data-testid="stSidebar"] * { color: #cbd5e1 !important; }
        .stTextInput > div > div > input, .stNumberInput > div > div > input, .stSelectbox > div > div > div {
            background: rgba(30, 41, 59, 0.6) !important; color: #f8fafc !important; border: 1px solid rgba(56, 189, 248, 0.3) !important; border-radius: 8px !important; transition: all 0.3s;
        }
        .stTextInput > div > div > input:focus { border-color: #38bdf8 !important; box-shadow: 0 0 10px rgba(56, 189, 248, 0.2); }
        [data-testid="stMetric"] { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 20px !important; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2); }
        [data-testid="stMetricLabel"] { color: #94a3b8 !important; font-weight: 600; }
        [data-testid="stMetricValue"] { background: -webkit-linear-gradient(45deg, #38bdf8, #06b6d4); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800 !important; }
        .stButton > button { background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%) !important; color: white !important; border: none !important; border-radius: 8px !important; font-weight: 600 !important; box-shadow: 0 4px 15px rgba(14, 165, 233, 0.3); transition: all 0.3s ease; }
        .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(14, 165, 233, 0.5); }
        .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: rgba(15, 23, 42, 0.5); padding: 6px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.05); }
        .stTabs [data-baseweb="tab"] { background-color: transparent; border-radius: 8px; padding: 10px 24px; color: #94a3b8 !important; font-weight: 600; border: none; transition: all 0.2s; }
        .stTabs [data-baseweb="tab"]:hover { background-color: rgba(255, 255, 255, 0.05); }
        .stTabs [aria-selected="true"] { background: rgba(56, 189, 248, 0.15) !important; color: #38bdf8 !important; border-bottom: 2px solid #38bdf8 !important; }
        [data-testid="stFileUploadDropzone"] { background: rgba(30, 41, 59, 0.4) !important; border: 2px dashed rgba(56, 189, 248, 0.3) !important; border-radius: 12px; transition: all 0.3s; }
        [data-testid="stFileUploadDropzone"]:hover { border-color: #38bdf8 !important; }
        [data-testid="stFileUploadDropzone"] * { color: #cbd5e1 !important; }
        [data-testid="stChatMessage"] { background-color: rgba(30, 41, 59, 0.7) !important; border: 1px solid rgba(255, 255, 255, 0.05) !important; border-radius: 12px !important; padding: 12px !important; margin-bottom: 10px; }
        .stAlert { background: rgba(30, 41, 59, 0.8) !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; border-radius: 10px !important; backdrop-filter: blur(10px); }
        .stAlert * { color: #f8fafc !important; }
        [data-testid="stDataFrame"] * { color: #000000 !important; }
    </style>
    """, unsafe_allow_html=True)

st.set_page_config(page_title="智驭轮枢·工业智能诊断平台", layout="wide", initial_sidebar_state="collapsed")
inject_custom_css()

# ===================== 登录/注册认证模块 =====================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.current_user = ""

if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div style="background: rgba(30, 41, 59, 0.6); backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.1); border-radius: 20px 20px 0 0; padding: 30px 30px 10px 30px; box-shadow: 0 20px 40px rgba(0,0,0,0.4);">
            <h2 style="text-align: center; color: #38bdf8; margin-bottom: 5px; font-weight: 800;">智驭轮枢·工业智能诊断平台</h2>
            <p style="text-align: center; color: #94a3b8; font-size: 14px; margin-bottom: 10px; letter-spacing: 2px;">PREDICTIVE MAINTENANCE SYSTEM</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 使用 Tabs 实现登录和注册切换
        tab_login, tab_register = st.tabs(["🔐 账号登录", "📝 工程师注册"])
        
        with tab_login:
            login_user = st.text_input("账号", key="login_user")
            login_pass = st.text_input("密码", type="password", key="login_pass")
            if st.button("🚀 安全登录", use_container_width=True):
                if verify_user(login_user, login_pass):
                    st.session_state.logged_in = True
                    st.session_state.current_user = login_user
                    st.success("身份验证成功，正在进入系统...")
                    time.sleep(0.8)
                    st.rerun()
                else:
                    st.error("❌ 账号或密码错误")
                    
        with tab_register:
            reg_user = st.text_input("设置新账号", key="reg_user")
            reg_pass = st.text_input("设置密码", type="password", key="reg_pass")
            reg_pass2 = st.text_input("确认密码", type="password", key="reg_pass2")
            if st.button("✨ 注册新账号", use_container_width=True):
                if not reg_user or not reg_pass:
                    st.warning("账号和密码不能为空！")
                elif reg_pass != reg_pass2:
                    st.error("两次输入的密码不一致！")
                elif add_user(reg_user, reg_pass):
                    st.success("🎉 注册成功！请切换到上方【账号登录】进行登录。")
                else:
                    st.error("该账号已存在，请换一个用户名。")
    st.stop()

# ===================== 物理尺寸与全局参数配置区 =====================
BALL_RADIUS = 12.0 
SEG_LEN = 1024
STEP = 1024
RANDOM_SEED = 42
LABEL_DICT = {0: "正常", 1: "内圈故障", 2: "外圈故障", 3: "滚动体故障"}
LABEL_LIST = list(LABEL_DICT.values())
CLASS_NUM = len(LABEL_DICT)

FEATURE_NAMES = ["标准差", "偏度", "峭度", "峰值因子", "脉冲因子", "频谱重心", "包络谱峰值", "包络谱能量"]

# ===================== CWRU 映射表 =====================
CWRU_FILE_MAP = {97: 0, 105: 1, 118: 3, 130: 2, 98: 0, 106: 1, 119: 3, 131: 2, 99: 0, 107: 1, 120: 3, 132: 2, 100: 0, 108: 1, 121: 3, 133: 2, 169: 1, 185: 3, 197: 2, 170: 1, 186: 3, 198: 2, 171: 1, 187: 3, 199: 2, 172: 1, 188: 3, 200: 2, 209: 1, 222: 3, 234: 2, 210: 1, 223: 3, 235: 2}
CWRU_LOAD_MAP = {97: 0, 105: 0, 118: 0, 130: 0, 169: 0, 185: 0, 197: 0, 98: 1, 106: 1, 119: 1, 131: 1, 170: 1, 186: 1, 198: 1, 99: 2, 107: 2, 120: 2, 132: 2, 171: 2, 187: 2, 199: 2, 209: 2, 222: 2, 234: 2, 100: 3, 108: 3, 121: 3, 133: 3, 172: 3, 188: 3, 200: 3, 210: 3, 223: 3, 235: 3}

# ===================== 扣子 AI 交互函数 =====================
def chat_with_bot(user_message):
    if not COZE_API_KEY or COZE_API_KEY == "pat_填入你新生成的Token": return "⚠️ 请先配置 COZE_API_KEY。"
    url = "https://api.coze.cn/v3/chat"
    headers = {"Authorization": f"Bearer {COZE_API_KEY}", "Content-Type": "application/json"}
    payload = {"bot_id": COZE_BOT_ID, "user_id": "streamlit_user", "stream": False, "auto_save_history": True, "additional_messages": [{"role": "user", "content": user_message, "content_type": "text"}]}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        data = response.json()
        if data.get("code") != 0: return f"API 报错: {data.get('msg')}"
        chat_id = data["data"]["id"]; conversation_id = data["data"]["conversation_id"]
        retrieve_url = "https://api.coze.cn/v3/chat/retrieve"
        for _ in range(30):
            status_resp = requests.get(retrieve_url, headers=headers, params={"chat_id": chat_id, "conversation_id": conversation_id}, timeout=10).json()
            data_detail = status_resp.get("data", {}); status = data_detail.get("status"); last_error = data_detail.get("last_error")
            if status == "failed":
                if last_error and last_error.get("code") == 4028: return "⚠️ 扣子大模型免费额度已用尽。请明日再试或前往扣子平台充值。"
                return f"❌ 对话失败！原因: {last_error.get('msg', '未知')}"
            if status == "completed": break
            time.sleep(1)
        list_url = "https://api.coze.cn/v3/chat/message/list"
        msg_resp = requests.get(list_url, headers=headers, params={"chat_id": chat_id, "conversation_id": conversation_id}, timeout=10).json()
        for msg in msg_resp.get("data", []):
            if msg.get("type") == "answer": return msg.get("content", "AI 未返回内容。")
        return "未在消息列表中找到 AI 的回复。"
    except Exception as e: return f"网络连接异常: {str(e)}"

# ===================== 核心算法函数 =====================
def add_awgn(signal, snr_db):
    signal_power = np.mean(signal ** 2); snr_linear = 10 ** (snr_db / 10.0); noise_power = signal_power / snr_linear
    return signal + np.random.normal(0, np.sqrt(noise_power), len(signal))

def parse_cwru_label(file_name: str, var_name: str = ""):
    m = re.search(r"(\d+)", file_name)
    if m and int(m.group(1)) in CWRU_FILE_MAP: return CWRU_FILE_MAP[int(m.group(1))]
    name = var_name.upper()
    if re.search(r"(IR|OR|B)\d", name) or re.search(r"_(IR|OR|B)_", name):
        if "IR" in name: return 1
        if "OR" in name: return 2
        if re.search(r"_B_|B\d", name): return 3
    if re.search(r"X\d+_DE_TIME", name): return 0
    return None

def parse_cwru_load(file_name: str):
    m = re.search(r"(\d+)", file_name)
    if m: return CWRU_LOAD_MAP.get(int(m.group(1)))
    return None

def load_cwru_file(uploaded_file):
    raw = scipy.io.loadmat(io.BytesIO(uploaded_file.read())); de_key = None
    for k in raw:
        if not k.startswith("__") and re.search(r"_DE_TIME$", k, re.IGNORECASE): de_key = k; break
    if not de_key:
        for k, v in raw.items():
            if not k.startswith("__"):
                arr = np.asarray(v, dtype=float).squeeze()
                if arr.ndim == 1 and arr.size > SEG_LEN: de_key = k; break
    if not de_key: raise ValueError("未找到一维信号")
    signal = np.asarray(raw[de_key], dtype=float).squeeze()
    return signal, parse_cwru_label(uploaded_file.name, de_key), parse_cwru_load(uploaded_file.name)

def segment_signal(signal, seg_len=SEG_LEN, step=STEP):
    n = (len(signal) - seg_len) // step + 1
    if n <= 0: return np.empty((0, seg_len))
    idx = np.arange(seg_len)[None, :] + step * np.arange(n)[:, None]
    return signal[idx]

def extract_features(segments, fs):
    feats = []
    for seg in segments:
        seg = seg.astype(float); std = np.std(seg); rms = np.sqrt(np.mean(seg ** 2)); peak = np.max(np.abs(seg)); mean_abs = np.mean(np.abs(seg))
        skew = np.mean((seg - np.mean(seg)) ** 3) / (std ** 3 + 1e-12); kurt = np.mean((seg - np.mean(seg)) ** 4) / (std ** 4 + 1e-12)
        crest = peak / (rms + 1e-12); impulse = peak / (mean_abs + 1e-12)
        spec = np.abs(np.fft.rfft(seg)); freqs = np.fft.rfftfreq(len(seg), d=1 / fs); spec_norm = spec / (np.sum(spec) + 1e-12); centroid = np.sum(freqs * spec_norm)
        env = np.abs(hilbert(seg)); env_spec = np.abs(np.fft.rfft(env - np.mean(env))); env_peak = np.max(env_spec); env_energy = np.sum(env_spec ** 2)
        feats.append([std, skew, kurt, crest, impulse, centroid, env_peak, env_energy])
    return np.array(feats, dtype=np.float32)

def get_records(signals_with_labels, fs):
    records = []
    for signal, label, load, fname in signals_with_labels:
        segs = segment_signal(signal)
        if len(segs) > 0: records.append({"fname": fname, "label": label, "load": load, "segs": segs, "X": extract_features(segs, fs)})
    return records

def stack_records(records):
    if not records: return None, None
    return np.vstack([r["X"] for r in records]), np.concatenate([[r["label"]] * len(r["X"]) for r in records])

# ===================== 3D 渲染与图表 =====================
def render_bearing_3d(fault_class):
    fig = go.Figure(); metal_lighting = dict(ambient=0.7, diffuse=0.5, specular=2.0, roughness=0.1, fresnel=0.9)
    inner_path, outer_path, cage_path = "inner_ring.stl", "outer_ring.stl", "cage.stl"
    inner_v, outer_v = None, None
    metal_color, fault_color, cage_color = "#6B6B6B", "#CC0000", "#CD7F32"  
    if os.path.exists(inner_path):
        try:
            m = trimesh.load(inner_path, force='mesh'); c = (m.vertices.max(axis=0) + m.vertices.min(axis=0)) / 2.0; inner_v = m.vertices - c
            color = fault_color if fault_class == "内圈故障" else ("#00CC00" if fault_class == "正常" else metal_color)
            fig.add_trace(go.Mesh3d(x=inner_v[:,0], y=inner_v[:,1], z=inner_v[:,2], i=m.faces[:,0], j=m.faces[:,1], k=m.faces[:,2], color=color, opacity=1.0, name="内圈", lighting=metal_lighting))
        except: pass
    if os.path.exists(outer_path):
        try:
            m = trimesh.load(outer_path, force='mesh'); c = (m.vertices.max(axis=0) + m.vertices.min(axis=0)) / 2.0; outer_v = m.vertices - c
            color = fault_color if fault_class == "外圈故障" else ("#00CC00" if fault_class == "正常" else metal_color)
            fig.add_trace(go.Mesh3d(x=outer_v[:,0], y=outer_v[:,1], z=outer_v[:,2], i=m.faces[:,0], j=m.faces[:,1], k=m.faces[:,2], color=color, opacity=1.0, name="外圈", lighting=metal_lighting))
        except: pass
    if os.path.exists(cage_path):
        try:
            m = trimesh.load(cage_path, force='mesh'); c = (m.vertices.max(axis=0) + m.vertices.min(axis=0)) / 2.0; cage_v = m.vertices - c
            fig.add_trace(go.Mesh3d(x=cage_v[:,0], y=cage_v[:,1], z=cage_v[:,2], i=m.faces[:,0], j=m.faces[:,1], k=m.faces[:,2], color=cage_color, opacity=1.0, name="保持架", lighting=metal_lighting))
        except: pass
    if inner_v is not None and outer_v is not None:
        try:
            extents = outer_v.max(axis=0) - outer_v.min(axis=0); axis_order = np.argsort(extents)[::-1]; axis1, axis2 = axis_order[0], axis_order[1]
            r_in = np.max(np.linalg.norm(inner_v[:, [axis1, axis2]], axis=1)); r_out_min = np.min(np.linalg.norm(outer_v[:, [axis1, axis2]], axis=1))
            TRACK_RADIUS = (r_in + r_out_min) / 2.0; ball_color = fault_color if fault_class == "滚动体故障" else ("#00CC00" if fault_class == "正常" else metal_color)
            sphere = trimesh.creation.icosphere(subdivisions=4, radius=BALL_RADIUS); sf = sphere.faces
            for i in range(8):
                angle = i * (2 * np.pi / 8); center = np.zeros(3); center[axis1] = TRACK_RADIUS * np.cos(angle); center[axis2] = TRACK_RADIUS * np.sin(angle)
                sv = sphere.vertices + center
                fig.add_trace(go.Mesh3d(x=sv[:,0], y=sv[:,1], z=sv[:,2], i=sf[:,0], j=sf[:,1], k=sf[:,2], color=ball_color, opacity=1.0, showlegend=False, lighting=metal_lighting))
        except: pass
    fig.update_layout(scene=dict(xaxis=dict(showbackground=False, showgrid=False, visible=False), yaxis=dict(showbackground=False, showgrid=False, visible=False), zaxis=dict(showbackground=False, showgrid=False, visible=False), aspectmode='data', camera=dict(up=dict(x=0, y=0, z=1), eye=dict(x=1.5, y=1.5, z=1.5))), margin=dict(l=0, r=0, b=0, t=0), height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig

def plot_signal_analysis(sig, fs):
    plot_len = min(len(sig), 4096); time = np.arange(plot_len) / fs; fig, axes = plt.subplots(2, 1, figsize=(10, 6), facecolor='#0f172a')
    axes[0].set_facecolor('#0f172a'); axes[0].plot(time, sig[:plot_len], color='#38bdf8', linewidth=0.8); axes[0].set_title("时域波形 (局部截取)", fontsize=12, color='#e2e8f0'); axes[0].tick_params(colors='#94a3b8'); axes[0].grid(True, linestyle='--', alpha=0.2, color='#334155')
    env = np.abs(hilbert(sig)); env_spec = np.abs(np.fft.rfft(env - np.mean(env))); freqs = np.fft.rfftfreq(len(sig), d=1/fs); max_freq = min(500, fs / 2); valid_idx = freqs <= max_freq
    axes[1].set_facecolor('#0f172a'); axes[1].plot(freqs[valid_idx], env_spec[valid_idx], color='#ef4444', linewidth=1.2); axes[1].set_title("Hilbert 包络谱 (提取故障特征频率)", fontsize=12, color='#e2e8f0'); axes[1].tick_params(colors='#94a3b8'); axes[1].grid(True, linestyle='--', alpha=0.2, color='#334155')
    plt.tight_layout(); return fig

# ===================== 主界面 =====================
st.title("🛞 智驭轮枢·跨设备高泛化轴承故障诊断系统")

with st.sidebar:
    st.success(f"👨‍🔧 当前身份：{st.session_state.current_user}")
    if st.button("🚪 退出登录"):
        st.session_state.logged_in = False; st.rerun()
    st.divider()
    st.header("1. 上传训练集 (CWRU)")
    uploaded_files = st.file_uploader("选择 CWRU .mat 文件", type=["mat"], accept_multiple_files=True)
    st.header("2. 全局配置")
    fs_train = st.number_input("训练集采样率 (Hz)", min_value=1000, max_value=100000, value=12000, step=1000)
    st.divider()
    st.subheader("⚙️ 评估配置")
    eval_mode = st.radio("评估模式", ["多次随机划分取平均", "按负载分组测试（留一负载）"])
    if eval_mode == "多次随机划分取平均":
        test_ratio = st.slider("测试文件比例", 0.1, 0.5, 0.3, 0.05); n_repeats = st.slider("重复次数", 5, 50, 10, 5)
    st.divider()
    st.subheader("📡 抗噪鲁棒性测试")
    enable_noise = st.checkbox("开启高斯白噪声干扰")
    if enable_noise:
        snr_db = st.slider("信噪比 (SNR / dB)", min_value=-10, max_value=20, value=0, step=1); noise_mode = st.radio("加噪策略", ["同时加噪训练和测试", "仅测试集加噪"])
    train_btn = st.button("🚀 训练并评估", use_container_width=True)
    st.divider()
    st.subheader("🤖 AI 专家在线答疑")
    if "chat_history" not in st.session_state: st.session_state.chat_history = []
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])
    if prompt := st.chat_input("向专家提问..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                response = chat_with_bot(prompt); st.markdown(response)
        st.session_state.chat_history.append({"role": "assistant", "content": response})

# ===================== 训练主逻辑 =====================
if train_btn:
    if not uploaded_files: st.error("请至少上传一个 .mat 文件")
    else:
        signals = []
        for f in uploaded_files:
            try:
                sig, lab, load = load_cwru_file(f)
                if lab is not None:
                    if enable_noise and noise_mode == "同时加噪训练和测试": sig = add_awgn(sig, snr_db)
                    signals.append((sig, lab, load, f.name))
            except Exception as e: st.error(f"{f.name} 读取失败: {e}")
        if len(signals) < 2: st.error("有效文件少于 2 个")
        else:
            if eval_mode == "多次随机划分取平均":
                rng = np.random.RandomState(RANDOM_SEED); n_files = len(signals); accs, f1s = [], []; cm_total = np.zeros((CLASS_NUM, CLASS_NUM), dtype=int)
                with st.spinner("正在评估..."):
                    for it in range(n_repeats):
                        n_test = max(1, int(round(n_files * test_ratio))); n_test = min(n_test, n_files - 1); perm = rng.permutation(n_files); test_idx = set(perm[:n_test].tolist())
                        tr_sigs = [signals[i] for i in range(n_files) if i not in test_idx]; te_sigs = [signals[i] for i in range(n_files) if i in test_idx]
                        if enable_noise and noise_mode == "仅测试集加噪": te_sigs = [(add_awgn(sig, snr_db), lab, load, fname) for (sig, lab, load, fname) in te_sigs]
                        X_tr, y_tr = stack_records(get_records(tr_sigs, fs_train)); X_te, y_te = stack_records(get_records(te_sigs, fs_train))
                        scaler = StandardScaler().fit(X_tr); clf = RandomForestClassifier(n_estimators=200, random_state=RANDOM_SEED+it, n_jobs=-1).fit(scaler.transform(X_tr), y_tr); y_pred = clf.predict(scaler.transform(X_te))
                        accs.append(accuracy_score(y_te, y_pred)); f1s.append(f1_score(y_te, y_pred, average="weighted")); cm_total += confusion_matrix(y_te, y_pred, labels=list(range(CLASS_NUM)))
                st.subheader(f"📊 {n_repeats} 次随机划分评估结果")
                c1, c2, c3 = st.columns(3); c1.metric("测试准确率均值", f"{np.mean(accs)*100:.2f}%"); c2.metric("准确率标准差", f"{np.std(accs)*100:.2f}%"); c3.metric("加权 F1 均值", f"{np.mean(f1s):.4f}")
                st.dataframe(pd.DataFrame(cm_total, index=[f"真:{n}" for n in LABEL_LIST], columns=[f"预:{n}" for n in LABEL_LIST]))
            elif eval_mode == "按负载分组测试（留一负载）":
                loads = sorted({s[2] for s in signals if s[2] is not None})
                if len(loads) < 2: st.error("需要至少 2 种负载的文件才能进行此项测试。")
                else:
                    results = []; cm_total = np.zeros((CLASS_NUM, CLASS_NUM), dtype=int)
                    with st.spinner("正在做留一负载交叉验证..."):
                        for test_load in loads:
                            tr_sigs = [s for s in signals if s[2] != test_load]; te_sigs = [s for s in signals if s[2] == test_load]
                            if enable_noise and noise_mode == "仅测试集加噪": te_sigs = [(add_awgn(sig, snr_db), lab, load, fname) for (sig, lab, load, fname) in te_sigs]
                            X_tr, y_tr = stack_records(get_records(tr_sigs, fs_train)); X_te, y_te = stack_records(get_records(te_sigs, fs_train))
                            scaler = StandardScaler().fit(X_tr); clf = RandomForestClassifier(n_estimators=200, random_state=RANDOM_SEED, n_jobs=-1).fit(scaler.transform(X_tr), y_tr); y_pred = clf.predict(scaler.transform(X_te))
                            acc = accuracy_score(y_te, y_pred); f1 = f1_score(y_te, y_pred, average="weighted"); cm_total += confusion_matrix(y_te, y_pred, labels=list(range(CLASS_NUM)))
                            results.append({"test_load": test_load, "n_train": len(X_tr), "n_test": len(X_te), "acc": acc, "f1": f1})
                    st.subheader("📊 留一负载交叉验证（跨工况泛化）")
                    c1, c2, c3 = st.columns(3); c1.metric("跨负载准确率均值", f"{np.mean([r['acc'] for r in results])*100:.2f}%"); c2.metric("准确率标准差", f"{np.std([r['acc'] for r in results])*100:.2f}%"); c3.metric("加权 F1 均值", f"{np.mean([r['f1'] for r in results]):.4f}")
                    st.subheader("各负载测试结果"); st.dataframe(pd.DataFrame([{"测试负载": f"{r['test_load']} HP", "训练样本数": r["n_train"], "测试样本数": r["n_test"], "准确率": f"{r['acc']*100:.2f}%", "加权 F1": f"{r['f1']:.4f}"} for r in results]))
                    st.subheader("累加混淆矩阵"); st.dataframe(pd.DataFrame(cm_total, index=[f"真:{n}" for n in LABEL_LIST], columns=[f"预:{n}" for n in LABEL_LIST]))
            X_all, y_all = stack_records(get_records(signals, fs_train)); scaler_final = StandardScaler().fit(X_all)
            clf_final = RandomForestClassifier(n_estimators=200, random_state=RANDOM_SEED, n_jobs=-1).fit(scaler_final.transform(X_all), y_all); st.session_state["model"] = (scaler_final, clf_final)

# ===================== 预测逻辑 =====================
if "model" in st.session_state:
    st.divider(); st.header("🔍 跨设备/新数据预测")
    col1, col2 = st.columns(2)
    with col1: pred_fs = st.number_input("待测设备的采样率 (Hz)", min_value=1000, max_value=100000, value=12000, step=1000)
    pred_file = st.file_uploader("上传待预测文件 (支持 .mat 或 .csv)", type=["mat", "csv"], key="pred")
    if pred_file is not None:
        try:
            if pred_file.name.endswith(".csv"):
                df = pd.read_csv(pred_file, header=None, on_bad_lines='skip', sep=None, engine='python'); df_numeric = df.apply(pd.to_numeric, errors='coerce').dropna(how='all')
                sig = df_numeric[df_numeric.var().idxmax()].dropna().values.astype(float) if df_numeric.shape[1] > 1 else df_numeric.iloc[:, 0].dropna().values.astype(float)
            else:
                raw = scipy.io.loadmat(io.BytesIO(pred_file.read())); de_key = next((k for k in raw if not k.startswith("__") and re.search(r"_DE_TIME$", k, re.IGNORECASE)), None)
                sig = np.asarray(raw[de_key or next(k for k, v in raw.items() if not k.startswith("__"))], dtype=float).squeeze()
            st.success(f"文件读取成功，共解析出 {len(sig)} 个有效采样点。")
            if enable_noise: sig = add_awgn(sig, snr_db); st.warning(f"⚠️ 注意：当前待预测文件已被注入 **{snr_db}dB** 的高斯白噪声！")
            segs = segment_signal(sig)
            if len(segs) == 0: st.error("信号长度不足以切片。")
            else:
                scaler, clf = st.session_state["model"]; feats = extract_features(segs, pred_fs); preds = clf.predict(scaler.transform(feats))
                values, counts = np.unique(preds, return_counts=True); final = values[np.argmax(counts)]; vote_dict = {LABEL_DICT[v]: int(c) for v, c in zip(values, counts)}
                st.markdown(f"""<div style="background: rgba(0, 200, 83, 0.15); border-left: 5px solid #00c853; padding: 20px; border-radius: 8px; margin-bottom: 20px;"><h3 style="margin:0; color: #fff;">最终诊断结果：<span style="color: #00c853;">{LABEL_DICT[final]}</span></h3><p style="margin-top: 10px; color: #94a3b8; font-size: 14px;">切片投票分布（共切出 {len(preds)} 个窗口）：{vote_dict}</p></div>""", unsafe_allow_html=True)
                st.markdown("---"); st.subheader("💡 AI 专家维修建议")
                with st.spinner("AI 专家正在根据诊断结果生成维修方案..."):
                    auto_prompt = f"系统刚刚诊断出当前轴承状态为：{LABEL_DICT[final]}。请直接给出3条以内最核心的维修建议和排查方向，语言要简练专业。"
                    auto_advice = chat_with_bot(auto_prompt); st.info(auto_advice)
                st.markdown("---")
                tab_macro, tab_micro, tab_signal, tab_math = st.tabs(["🏭 宏观：减速器", "⚙️ 微观：轴承 3D", "📊 信号解析", "📐 数学模型"])
                with tab_macro:
                    if os.path.exists("gearbox.png"):
                        c1, c2, c3 = st.columns([1, 2, 1])
                        with c2: st.image("gearbox.png", use_container_width=True)
                        if LABEL_DICT[final] == "正常": st.success("✅ 减速器整体运行平稳。")
                        else: st.error(f"🚨 **异常警报**：红圈所示输入端轴承检测到 **{LABEL_DICT[final]}**！")
                    else: st.warning("⚠️ 未找到减速器图片，请将图片命名为 `gearbox.png` 放入 assets 文件夹。")
                with tab_micro: st.plotly_chart(render_bearing_3d(LABEL_DICT[final]), use_container_width=True)
                with tab_signal: st.pyplot(plot_signal_analysis(sig, pred_fs))
                with tab_math:
                    st.latex(r"Kurtosis = \frac{\frac{1}{N} \sum_{i=1}^{N} (x_i - \bar{x})^4}{\sigma^4}"); st.caption("**峭度**：对微弱冲击极其敏感。")
                    st.latex(r"\hat{x}(t) = \frac{1}{\pi} \int_{-\infty}^{\infty} \frac{x(\tau)}{t - \tau} d\tau"); st.caption("**希尔伯特变换**：用于提取包络信号。")
        except Exception as e: st.error(f"预测失败: {e}")
