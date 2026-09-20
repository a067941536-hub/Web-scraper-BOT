import streamlit as st
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageOps
import easyocr
import numpy as np
import urllib.parse
import re
import base64
import io
import os
import json
from contextlib import contextmanager
from difflib import SequenceMatcher
from html import escape as esc
from pathlib import Path

# 1. 頁面基本設定 (隱藏預設側邊欄)
st.set_page_config(
    page_title="擷取工具",
    page_icon="ღ",
    layout="wide",
    initial_sidebar_state="collapsed"
)

SETTINGS_PATH = Path(".app_settings.json")   # 本機設定 (主題 / 模型 / 選擇性儲存 Key)
BG_PATH = Path(".app_bg.jpg")                # 本機背景圖
MODEL_OPTIONS = ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.5-pro", "自訂..."]

# -------------------------------------------------------------------
# 2. HTML 渲染終極修正函數 (徹底消除每行開頭空格與空行，防 Markdown 誤判)
# -------------------------------------------------------------------
def render_html(html_str):
    clean_str = "\n".join(line.strip() for line in html_str.splitlines() if line.strip())
    st.markdown(clean_str, unsafe_allow_html=True)


@contextmanager
def main_card():
    """與原本相同：頁面開頭輸出 main-card，結尾輸出 </div>。"""
    render_html('<div class="main-card">')
    try:
        yield
    finally:
        render_html('</div>')


def valid_url(u):
    p = urllib.parse.urlparse(u.strip())
    return p.scheme in ("http", "https") and bool(p.netloc)


def safe_href(u):
    return esc(u, quote=True) if valid_url(u) else "#"


def clean_text(s):
    return re.sub(r"\s+", " ", s).strip()


def highlight(text, kw):
    """先跳脫 HTML，再把關鍵字包上 <mark>。"""
    safe = esc(text)
    if not kw:
        return safe
    pat = re.compile(re.escape(esc(kw)), re.IGNORECASE)
    return pat.sub(lambda m: f"<mark>{m.group(0)}</mark>", safe)

# -------------------------------------------------------------------
# 3. 設定持久化 (本機 JSON，重新整理後不會遺失) + Session 狀態初始化
# -------------------------------------------------------------------
def load_settings():
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_settings():
    data = {
        "theme_mode": st.session_state.get("theme_mode", "暗黑極光"),
        "model_choice": st.session_state.get("model_choice", MODEL_OPTIONS[0]),
        "custom_model": st.session_state.get("custom_model", ""),
        "remember_key": bool(st.session_state.get("remember_key", False)),
    }
    if data["remember_key"]:
        data["api_key"] = st.session_state.get("api_key", "")
    try:
        SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.chmod(SETTINGS_PATH, 0o600)
    except Exception:
        pass


def get_secret_key():
    try:
        v = st.secrets.get("GEMINI_API_KEY", "")
        if v:
            return v
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY", "")


def process_bg(file_bytes):
    """縮圖並統一轉成 JPEG，降低 CSS 內嵌的資料量。"""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(file_bytes))).convert("RGB")
    img.thumbnail((1920, 1080))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


if "_initialized" not in st.session_state:
    saved = load_settings()
    st.session_state.theme_mode = saved.get("theme_mode", "暗黑極光")
    st.session_state.model_choice = saved.get("model_choice", MODEL_OPTIONS[0])
    st.session_state.custom_model = saved.get("custom_model", "")
    st.session_state.remember_key = saved.get("remember_key", False)
    st.session_state.api_key = get_secret_key() or saved.get("api_key", "")
    st.session_state.bg_image_b64 = (
        base64.b64encode(BG_PATH.read_bytes()).decode("utf-8") if BG_PATH.exists() else None
    )
    st.session_state.bg_uploader_ver = 0
    st.session_state.bg_notice = None
    st.session_state.search = None
    st.session_state.url_result = None
    st.session_state.ocr_sig = None
    st.session_state.ai_answer = ""
    st.session_state._initialized = True

# -------------------------------------------------------------------
# 4. 主題配色 (「暗黑極光」= 你原本的配色，外觀完全不變)
# -------------------------------------------------------------------
THEME_CONFIGS = {
    "暗黑極光": {
        "bg_app": "#0b0f19",
        "main_bg": "rgba(15, 23, 42, 0.22)", "main_border": "rgba(255, 255, 255, 0.2)",
        "main_shadow": "0 16px 40px rgba(0, 0, 0, 0.35)",
        "card_bg": "rgba(15, 23, 42, 0.8)", "card_hover_bg": "rgba(15, 23, 42, 0.9)",
        "card_border": "rgba(255, 255, 255, 0.18)", "card_hover_border": "rgba(56, 189, 248, 0.6)",
        "card_shadow": "0 8px 20px rgba(0, 0, 0, 0.3)",
        "summary_bg": "rgba(15, 23, 42, 0.85)",
        "nav_bg": "rgba(15, 23, 42, 0.75)", "nav_border": "rgba(255, 255, 255, 0.25)",
        "nav_text": "#ffffff", "nav_shadow": "0 8px 24px rgba(0, 0, 0, 0.3)",
        "nav_hover_bg": "rgba(255, 255, 255, 0.25)", "nav_hover_border": "#ffffff",
        "nav_hover_shadow": "0 10px 25px rgba(255, 255, 255, 0.3)",
        "nav_active_bg": "#ffffff", "nav_active_border": "#ffffff", "nav_active_text": "#0f172a",
        "nav_active_shadow": "0 10px 28px rgba(255, 255, 255, 0.5)",
        "input_bg": "rgba(15, 23, 42, 0.85)", "input_text": "#ffffff",
        "input_border": "rgba(255, 255, 255, 0.2)",
        "text_primary": "#f8fafc", "text_secondary": "#cbd5e1", "text_muted": "#94a3b8", "text_body": "#e2e8f0",
        "accent": "#38bdf8", "accent2": "#c084fc",
        "head_shadow": "0 2px 4px rgba(0,0,0,0.8)",
        "badge_bg": "rgba(15, 23, 42, 0.8)", "badge_border": "rgba(56, 189, 248, 0.4)",
    },
    "極致純白": {
        "bg_app": "#F1F5F9",
        "main_bg": "rgba(255, 255, 255, 0.55)", "main_border": "rgba(0, 0, 0, 0.12)",
        "main_shadow": "0 12px 32px rgba(0, 0, 0, 0.10)",
        "card_bg": "rgba(255, 255, 255, 0.92)", "card_hover_bg": "#ffffff",
        "card_border": "rgba(0, 0, 0, 0.12)", "card_hover_border": "rgba(37, 99, 235, 0.6)",
        "card_shadow": "0 8px 20px rgba(0, 0, 0, 0.08)",
        "summary_bg": "rgba(255, 255, 255, 0.95)",
        "nav_bg": "rgba(255, 255, 255, 0.85)", "nav_border": "rgba(0, 0, 0, 0.15)",
        "nav_text": "#1E293B", "nav_shadow": "0 8px 24px rgba(0, 0, 0, 0.10)",
        "nav_hover_bg": "rgba(37, 99, 235, 0.12)", "nav_hover_border": "#2563EB",
        "nav_hover_shadow": "0 10px 25px rgba(37, 99, 235, 0.25)",
        "nav_active_bg": "linear-gradient(135deg, #2563EB, #4F46E5)", "nav_active_border": "transparent",
        "nav_active_text": "#ffffff", "nav_active_shadow": "0 10px 28px rgba(37, 99, 235, 0.45)",
        "input_bg": "rgba(255, 255, 255, 0.98)", "input_text": "#0F172A",
        "input_border": "rgba(0, 0, 0, 0.18)",
        "text_primary": "#0F172A", "text_secondary": "#334155", "text_muted": "#475569", "text_body": "#1E293B",
        "accent": "#2563EB", "accent2": "#7C3AED",
        "head_shadow": "none",
        "badge_bg": "rgba(255, 255, 255, 0.9)", "badge_border": "rgba(37, 99, 235, 0.4)",
    },
    "賽博霓虹": {
        "bg_app": "#070b16",
        "main_bg": "rgba(10, 15, 30, 0.35)", "main_border": "rgba(56, 189, 248, 0.35)",
        "main_shadow": "0 0 28px rgba(56, 189, 248, 0.25)",
        "card_bg": "rgba(10, 15, 30, 0.85)", "card_hover_bg": "rgba(10, 15, 30, 0.95)",
        "card_border": "rgba(56, 189, 248, 0.3)", "card_hover_border": "rgba(217, 70, 239, 0.7)",
        "card_shadow": "0 0 20px rgba(56, 189, 248, 0.2)",
        "summary_bg": "rgba(10, 15, 30, 0.9)",
        "nav_bg": "rgba(15, 23, 42, 0.7)", "nav_border": "rgba(56, 189, 248, 0.35)",
        "nav_text": "#7DD3FC", "nav_shadow": "0 0 18px rgba(56, 189, 248, 0.2)",
        "nav_hover_bg": "rgba(217, 70, 239, 0.25)", "nav_hover_border": "#D946EF",
        "nav_hover_shadow": "0 0 25px rgba(217, 70, 239, 0.4)",
        "nav_active_bg": "linear-gradient(135deg, #D946EF, #8B5CF6)", "nav_active_border": "transparent",
        "nav_active_text": "#ffffff", "nav_active_shadow": "0 0 28px rgba(217, 70, 239, 0.55)",
        "input_bg": "rgba(15, 23, 42, 0.95)", "input_text": "#F0F9FF",
        "input_border": "rgba(56, 189, 248, 0.35)",
        "text_primary": "#E0F2FE", "text_secondary": "#7DD3FC", "text_muted": "#818CF8", "text_body": "#BAE6FD",
        "accent": "#22D3EE", "accent2": "#D946EF",
        "head_shadow": "0 0 8px rgba(56, 189, 248, 0.5)",
        "badge_bg": "rgba(10, 15, 30, 0.85)", "badge_border": "rgba(34, 211, 238, 0.5)",
    },
}

if st.session_state.theme_mode not in THEME_CONFIGS:
    st.session_state.theme_mode = "暗黑極光"
T = THEME_CONFIGS[st.session_state.theme_mode]

# -------------------------------------------------------------------
# 5. 動態 CSS 注入 (版型維持原樣，顏色改由主題變數控制)
# -------------------------------------------------------------------
root_vars = ":root {" + "".join(f"--{k.replace('_', '-')}: {v};" for k, v in T.items()) + "}"

if st.session_state.bg_image_b64:
    bg_rule = (
        ".stApp { background-color: var(--bg-app);"
        f' background-image: url("data:image/jpeg;base64,{st.session_state.bg_image_b64}");'
        " background-size: cover; background-position: center; background-attachment: fixed; }"
    )
else:
    bg_rule = ".stApp { background-color: var(--bg-app); }"

BASE_CSS = """
/* 完全隱藏預設側邊欄 */
section[data-testid="stSidebar"] { display: none !important; }

/* 全域文字顏色 (跟隨主題) */
.stApp p, .stApp span, .stApp h1, .stApp h2, .stApp h3,
.stApp h4, .stApp h5, .stApp h6, .stApp label, .stApp li {
    color: var(--text-primary) !important;
}
div[data-testid="stCaptionContainer"] * { color: var(--text-muted) !important; }
mark { background: rgba(250, 204, 21, 0.45); color: inherit; padding: 0 2px; border-radius: 3px; }

/* 頂部選單容器 */
div[data-testid="stRadio"] > div[role="radiogroup"] {
    display: flex !important;
    flex-wrap: wrap !important;
    justify-content: center !important;
    align-items: center !important;
    gap: 20px !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 10px 0 20px 0 !important;
}

/* 隱藏 Radio 原生圓圈與圖示 */
div[data-testid="stRadio"] input[type="radio"],
div[data-testid="stRadio"] label > div:first-child,
div[data-testid="stRadio"] label svg {
    display: none !important;
    width: 0 !important;
    height: 0 !important;
    opacity: 0 !important;
}

/* 個別頂部選單按鈕 */
div[data-testid="stRadio"] label {
    background: var(--nav-bg) !important;
    backdrop-filter: blur(8px) !important;
    border: 1px solid var(--nav-border) !important;
    border-radius: 16px !important;
    padding: 12px 26px !important;
    cursor: pointer !important;
    box-shadow: var(--nav-shadow) !important;
    transition: all 0.3s ease !important;
    margin: 0 !important;
}

/* 頂部選單內部文字 */
div[data-testid="stRadio"] label *,
div[data-testid="stRadio"] label p,
div[data-testid="stRadio"] label span {
    color: var(--nav-text) !important;
    font-size: 19px !important;
    font-weight: 700 !important;
    margin: 0 !important;
}

/* 上下跳動 Keyframes */
@keyframes hoverBounce {
    0%, 100% { transform: translateY(0px) scale(1.06); }
    50% { transform: translateY(-8px) scale(1.06); }
}

/* 選單懸停 (Hover) */
div[data-testid="stRadio"] label:hover {
    background: var(--nav-hover-bg) !important;
    border-color: var(--nav-hover-border) !important;
    animation: hoverBounce 1s infinite ease-in-out !important;
    box-shadow: var(--nav-hover-shadow) !important;
}

/* 當前選中的功能頁面 (Active) */
div[data-testid="stRadio"] label:has(input:checked) {
    background: var(--nav-active-bg) !important;
    border-color: var(--nav-active-border) !important;
    box-shadow: var(--nav-active-shadow) !important;
    transform: translateY(-4px) scale(1.06) !important;
}

div[data-testid="stRadio"] label:has(input:checked) *,
div[data-testid="stRadio"] label:has(input:checked) p,
div[data-testid="stRadio"] label:has(input:checked) span {
    color: var(--nav-active-text) !important;
}

/* 主外框面板：高透明度 + 超微弱模糊，背景底圖清晰可見 */
.main-card {
    background: var(--main-bg) !important;
    backdrop-filter: blur(3px) !important;
    -webkit-backdrop-filter: blur(3px) !important;
    border: 1px solid var(--main-border) !important;
    border-radius: 24px !important;
    padding: 36px !important;
    margin-bottom: 25px !important;
    box-shadow: var(--main-shadow) !important;
    color: var(--text-primary) !important;
}

/* 動態科技光束分割線 */
@keyframes cyberGlow {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
.cyber-line {
    height: 2px;
    width: 100%;
    background: linear-gradient(90deg, var(--accent), #818cf8, var(--accent2), var(--accent));
    background-size: 200% 200%;
    animation: cyberGlow 4s infinite ease;
    margin: 24px 0;
    border-radius: 2px;
}

/* 動態呼吸燈訊號 */
@keyframes pulseGlow {
    0% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7); transform: scale(1); }
    70% { box-shadow: 0 0 0 10px rgba(34, 197, 94, 0); transform: scale(1.1); }
    100% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); transform: scale(1); }
}
.pulse-dot {
    display: inline-block;
    width: 12px;
    height: 12px;
    background-color: #22c55e;
    border-radius: 50%;
    margin-right: 8px;
    animation: pulseGlow 2s infinite;
}

/* 科技感數據儀表網格 */
.tech-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 18px;
    margin: 20px 0;
}

/* 文字卡片 */
.tech-card {
    background: var(--card-bg) !important;
    border: 1px solid var(--card-border) !important;
    backdrop-filter: blur(12px) !important;
    border-radius: 16px;
    padding: 20px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: var(--card-shadow);
}
.tech-card:hover {
    background: var(--card-hover-bg) !important;
    border-color: var(--card-hover-border) !important;
    transform: translateY(-5px);
}

/* 摘要文字外框區塊 (HTML 版 + AI 解答容器共用) */
.summary-box, .st-key-ai_answer {
    background-color: var(--summary-bg) !important;
    border-left: 4px solid var(--accent2);
    padding: 16px 20px;
    border-radius: 12px;
    margin: 14px 0;
    backdrop-filter: blur(10px);
    box-shadow: var(--card-shadow);
}
.summary-box h4 { color: var(--accent) !important; }
.summary-box a { color: var(--accent2) !important; }

/* 輸入框不透明化，防止文字重疊背景 */
.stTextInput input, .stTextArea textarea,
.stSelectbox div[data-baseweb="select"] > div {
    background-color: var(--input-bg) !important;
    color: var(--input-text) !important;
    border: 1px solid var(--input-border) !important;
    border-radius: 8px !important;
}
.stSelectbox div[data-baseweb="select"] * { color: var(--input-text) !important; }
div[data-baseweb="popover"] ul, div[data-baseweb="popover"] li {
    background: var(--summary-bg) !important; color: var(--input-text) !important;
}

/* 按鈕 / 上傳框 / 提示框：跟隨主題，避免白色主題看不清楚 */
.stButton > button, .stDownloadButton > button, section[data-testid="stFileUploaderDropzone"] button {
    background: var(--nav-bg) !important; color: var(--nav-text) !important;
    border: 1px solid var(--nav-border) !important; border-radius: 12px !important; font-weight: 600 !important;
}
.stButton > button:hover, .stDownloadButton > button:hover { border-color: var(--accent) !important; }
.stButton > button p, .stDownloadButton > button p { color: inherit !important; }
section[data-testid="stFileUploaderDropzone"] {
    background: var(--input-bg) !important; border: 1px dashed var(--input-border) !important; border-radius: 12px !important;
}
section[data-testid="stFileUploaderDropzone"] * { color: var(--input-text) !important; }
section[data-testid="stFileUploaderDropzone"] button * { color: var(--nav-text) !important; }
div[data-testid="stAlert"] {
    background: var(--summary-bg) !important; border: 1px solid var(--card-border) !important; border-radius: 12px !important;
}
div[data-testid="stAlert"] * { color: var(--text-primary) !important; }
div[data-testid="stExpander"] { background: var(--card-bg); border: 1px solid var(--card-border) !important; border-radius: 12px; }
div[data-testid="stMetric"] { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; padding: 12px 16px; }
pre, code { background: var(--input-bg) !important; color: var(--input-text) !important; }

/* 手機版 */
@media (max-width: 768px) {
    div[data-testid="stRadio"] > div[role="radiogroup"] { gap: 8px !important; }
    div[data-testid="stRadio"] label { padding: 8px 12px !important; }
    div[data-testid="stRadio"] label *, div[data-testid="stRadio"] label p { font-size: 14px !important; }
    .main-card { padding: 18px !important; border-radius: 16px !important; }
    .tech-grid { grid-template-columns: 1fr; }
}

/* 系統偏好「減少動態效果」時關閉動畫 */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation: none !important; transition: none !important; }
}
"""

render_html("<style>" + root_vars + bg_rule + BASE_CSS + "</style>")

# -------------------------------------------------------------------
# 6. 頂部導覽列
# -------------------------------------------------------------------
nav_mode = st.radio(
    "功能選單",
    [
        "🏠 首頁",
        "🔍 關鍵字搜尋",
        "🌐 指定網址擷取",
        "🖼️ 截圖文字辨識",
        "🧠 自動解題",
        "⚙️ 設定"
    ],
    horizontal=True,
    label_visibility="collapsed"
)

# -------------------------------------------------------------------
# 7. 工具函數 (OCR / 搜尋 / 網頁 / AI)
# -------------------------------------------------------------------
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['ch_tra', 'en'])


@st.cache_data(show_spinner=False, max_entries=8)
def run_ocr(img_bytes, max_side=1600):
    """OCR 結果依圖片內容快取；大圖先縮小再辨識，座標換算回原圖。"""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(img_bytes))).convert("RGB")
    w, h = img.size
    scale = min(1.0, max_side / max(w, h))
    small = img.resize((int(w * scale), int(h * scale))) if scale < 1.0 else img
    raw = load_ocr().readtext(np.array(small))
    return [([[float(x) / scale, float(y) / scale] for x, y in bbox], text, float(prob)) for bbox, text, prob in raw]


def summarize_snippet(text):
    text = re.sub(r'\s+', ' ', text).strip()
    sentences = [s.strip() for s in re.split(r'[。！!？?\n]', text) if len(s.strip()) > 5]
    if not sentences:
        return ["• " + text] if text else ["• 暫無詳細摘要重點。"]
    return ["• " + s for s in sentences[:3]]


@st.cache_data(ttl=600, show_spinner=False)
def fetch_search_results(kw, max_results=8):
    """搜尋結果快取 10 分鐘；失敗時 raise，避免把空結果快取起來。"""
    results = []
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        for r in DDGS().text(kw, max_results=max_results):
            results.append({'title': r.get('title', ''), 'url': r.get('href', ''), 'snippet': r.get('body', '')})
    except Exception:
        results = []
    if results:
        return results

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0"}
        url = f"https://tw.search.yahoo.com/search?p={urllib.parse.quote(kw)}"
        res = requests.get(url, headers=headers, timeout=8)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            items = soup.find_all('div', class_='dd algo') or soup.find_all('div', class_='compTitle')
            for item in items[:max_results]:
                a_tag = item.find('a')
                if not a_tag:
                    continue
                title = a_tag.get_text().strip()
                href = a_tag.get('href', '')
                parent = item.find_parent('li') or item.parent
                snippet_elem = parent.find('div', class_='compText') or parent.find('p') if parent else None
                snippet = snippet_elem.get_text().strip() if snippet_elem else title
                if title and href:
                    results.append({'title': title, 'url': href, 'snippet': snippet})
    except Exception:
        pass

    if not results:
        raise RuntimeError("搜尋服務暫時無法使用")
    return results


@st.cache_data(ttl=600, show_spinner=False)
def fetch_page(url):
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    res.raise_for_status()
    # 沒有 charset 時 requests 會預設 ISO-8859-1，改用內容偵測，避免 Big5 等網站亂碼
    if not res.encoding or res.encoding.lower() == "iso-8859-1":
        res.encoding = res.apparent_encoding or "utf-8"
    soup = BeautifulSoup(res.text, 'html.parser')
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript", "svg"]):
        tag.decompose()
    title = clean_text(soup.title.get_text()) if soup.title else url
    seen, paragraphs = set(), []
    for el in soup.find_all(['p', 'h1', 'h2', 'h3', 'li']):
        t = clean_text(el.get_text())
        if len(t) > 10 and t not in seen:
            seen.add(t)
            paragraphs.append(t)
    return {"title": title, "paragraphs": paragraphs}


def get_model():
    if st.session_state.model_choice == "自訂...":
        return st.session_state.custom_model.strip() or MODEL_OPTIONS[0]
    return st.session_state.model_choice


def gemini_stream(key, model, prompt_text, pil_image=None):
    """串流呼叫 Gemini；Key 放在 header，不會出現在網址與日誌。"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse"
    headers = {"Content-Type": "application/json", "x-goog-api-key": key}
    parts = []
    if pil_image is not None:
        buf = io.BytesIO()
        pil_image.save(buf, format="JPEG", quality=90)
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()}})
    parts.append({"text": prompt_text})
    payload = {"contents": [{"parts": parts}]}
    try:
        with requests.post(url, json=payload, headers=headers, stream=True, timeout=(10, 120)) as r:
            if r.status_code != 200:
                yield f"❌ API 請求失敗 (HTTP {r.status_code})：{r.text[:500]}"
                return
            r.encoding = "utf-8"  # SSE 沒有 charset 時 requests 會誤判，導致中文亂碼
            got_any = False
            for line in r.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue
                try:
                    chunk = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
                for cand in chunk.get("candidates", []):
                    for part in cand.get("content", {}).get("parts", []):
                        if "text" in part:
                            got_any = True
                            yield part["text"]
            if not got_any:
                yield "❌ 無法解析 AI 回傳的資料（可能被安全機制攔截或模型名稱錯誤）。"
    except requests.RequestException as e:
        yield f"❌ 網路錯誤：{e}"


def gemini_text(prompt_text):
    return "".join(gemini_stream(st.session_state.api_key, get_model(), prompt_text))


def fuzzy_score(k, t):
    if not k or not t:
        return 0.0
    n = len(k)
    if len(t) <= n:
        return SequenceMatcher(None, k, t).ratio()
    best = 0.0
    for size in {max(1, n - 1), n, n + 1}:
        if size > len(t):
            continue
        for i in range(len(t) - size + 1):
            best = max(best, SequenceMatcher(None, k, t[i:i + size]).ratio())
    return best


def classify(text, keywords, fuzzy_on, threshold):
    t = text.strip().lower()
    for kw in keywords:
        if t == kw:
            return "exact", kw
    for kw in keywords:
        if kw in t:
            return "partial", kw
    if fuzzy_on:
        for kw in keywords:
            if fuzzy_score(kw, t) >= threshold:
                return "fuzzy", kw
    return None


def build_prompt(source_text, user_query):
    return f"""
你是一個極度聰明且嚴謹的 AI 智慧助理。
請自主分析使用者提供的【文字/圖片】與【問題指令】，並依據以下結構進行處理與回答：

---
### 🛠️ 1. 意圖判定與處理策略
（簡短說明判斷意圖：例如「題目解答」、「長文檢索與答案定位」等）

---
### 🎯 2. 核心解答 / 結論摘要
（直接給出最精準的答案、解題結果或核心重點）

---
### 📌 3. 原文/依據精準定位 (對照對應句)
（若資料來源為文章，請精準引用原文中的特定句子；若是解題，請說明題目給出的關鍵條件資訊）

---
### 🔍 4. 詳細推導步驟 / 邏輯解析
（按步驟提供詳細推導、解題過程、程式碼說明或觀念解析）

---
【使用者參考資料】：
{source_text if source_text.strip() else '（無提供純文字，請參考圖片或直接解答）'}

【問題/指令】：
{user_query if user_query.strip() else '請自主分析上方的文章或圖片，提煉重點並給出完整解答。'}
"""

# -------------------------------------------------------------------
# 8. 主功能面板區域
# -------------------------------------------------------------------

# (0) 🏠 首頁
def page_home():
    bg_status = "已載入個人視覺化桌布" if st.session_state.bg_image_b64 else "預設主題底色"
    api_status = "ONLINE (已連線)" if st.session_state.api_key else "OFFLINE (請至⚙️ 設定配置)"
    api_color = "#22c55e" if st.session_state.api_key else "#f43f5e"

    render_html(f"""
    <div class="main-card">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <div>
                <h1 style="margin: 0; font-size: 32px; font-weight: 800; background: linear-gradient(90deg, var(--accent), var(--accent2)); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                    🤖 智慧資訊擷取與 AI 輔助系統
                </h1>
                <p style="margin-top: 6px; color: var(--text-secondary) !important; font-size: 16px; font-weight: 600;">Next-Gen Intelligence & Multimodal Analytics Portal</p>
            </div>
            <div style="background: var(--badge-bg); padding: 8px 18px; border-radius: 30px; border: 1px solid var(--badge-border); display: flex; align-items: center;">
                <span class="pulse-dot"></span>
                <span style="font-weight: 700; font-size: 14px; color: var(--accent) !important;">SYSTEM READY</span>
            </div>
        </div>

        <div class="cyber-line"></div>

        <h3 style="color: var(--text-primary) !important; margin-top:0; text-shadow: var(--head-shadow);">⚡ 系統核心即時狀態 (Live System Status)</h3>
        <div class="tech-grid">
            <div class="tech-card">
                <div style="font-size: 13px; color: var(--text-muted) !important; font-weight: 600;">🖼️ 個人化視覺背景</div>
                <div style="font-size: 18px; font-weight: 700; margin-top: 8px; color: var(--accent) !important;">{bg_status}</div>
            </div>
            <div class="tech-card">
                <div style="font-size: 13px; color: var(--text-muted) !important; font-weight: 600;">🔑 AI 引擎狀態</div>
                <div style="font-size: 18px; font-weight: 700; margin-top: 8px; color: {api_color} !important;">{api_status}</div>
            </div>
            <div class="tech-card">
                <div style="font-size: 13px; color: var(--text-muted) !important; font-weight: 600;">🎨 目前介面主題</div>
                <div style="font-size: 18px; font-weight: 700; margin-top: 8px; color: var(--accent2) !important;">{esc(st.session_state.theme_mode)}</div>
            </div>
        </div>

        <div class="cyber-line"></div>

        <h3 style="color: var(--text-primary) !important; text-shadow: var(--head-shadow);">🚀 模組化功能導向 (Functional Modules)</h3>
        <div class="tech-grid">
            <div class="tech-card">
                <h4 style="margin: 0; color: var(--accent) !important;">🔍 關鍵字精準搜尋</h4>
                <p style="font-size: 14px; color: var(--text-body) !important; margin-top: 8px;">即時聯網檢索，自動提取網頁核心重點並條列化濃縮，可選用 AI 整體摘要。</p>
            </div>
            <div class="tech-card">
                <h4 style="margin: 0; color: var(--accent) !important;">🌐 指定網址擷取</h4>
                <p style="font-size: 14px; color: var(--text-body) !important; margin-top: 8px;">智慧解析目標網站段落結構，自動去除雜訊與重複，關鍵字高亮並可下載。</p>
            </div>
            <div class="tech-card">
                <h4 style="margin: 0; color: var(--accent2) !important;">🖼️ 截圖文字辨識</h4>
                <p style="font-size: 14px; color: var(--text-body) !important; margin-top: 8px;">EasyOCR 多國語言辨識，支援多關鍵字、模糊比對與標記圖下載。</p>
            </div>
            <div class="tech-card">
                <h4 style="margin: 0; color: var(--accent2) !important;">🧠 自動解題與推理</h4>
                <p style="font-size: 14px; color: var(--text-body) !important; margin-top: 8px;">Gemini 多模態 AI，串流即時輸出，自動識別題型、邏輯推導與原文句子定位。</p>
            </div>
        </div>
    </div>
    """)


# (1) 🔍 關鍵字搜尋
def do_search(kw, use_ai):
    with st.spinner(f"正在搜尋並濃縮「{kw}」..."):
        try:
            results = fetch_search_results(kw, 8)
        except Exception as e:
            st.session_state.search = {"kw": kw, "use_ai": use_ai, "error": str(e)}
            st.toast("搜尋失敗，請稍後重試", icon="⚠️")
            return
        ai_summary = None
        if use_ai and st.session_state.api_key:
            lines = "\n".join(
                f"{i}. {r['title']}\n   {clean_text(r['snippet'])[:300]}" for i, r in enumerate(results, 1)
            )
            ai_summary = gemini_text(
                f"以下是關於「{kw}」的搜尋結果，請用繁體中文整理 3~5 個整體重點（條列），"
                f"並在每點後標註對應的結果編號。不要編造資料以外的內容。\n\n{lines}"
            )
        st.session_state.search = {"kw": kw, "use_ai": use_ai, "results": results, "ai_summary": ai_summary}


def page_search():
    with main_card():
        st.header("🔍 關鍵字精準搜尋與智慧重點濃縮")
        keyword = st.text_input("請輸入搜尋關鍵字：", placeholder="例如：最新 AI 發展趨勢", key="search_kw")
        has_key = bool(st.session_state.api_key)
        use_ai = st.checkbox(
            "使用 AI 產生整體重點摘要" + ("" if has_key else "（需先設定 API Key）"),
            value=has_key, disabled=not has_key, key="search_use_ai",
        )

        if st.button("開始搜尋與濃縮", key="search_btn"):
            if not keyword.strip():
                st.warning("請先輸入關鍵字！")
            else:
                do_search(keyword.strip(), use_ai)

        s = st.session_state.search
        if not s:
            st.caption("輸入關鍵字後按下搜尋；同一關鍵字 10 分鐘內會直接使用快取結果。")
            return
        if s.get("error"):
            st.error(f"❌ 暫時無法連線至搜尋服務：{s['error']}")
            if st.button("🔁 重試", key="search_retry"):
                do_search(s["kw"], s["use_ai"])
                st.rerun()
            return

        results = s["results"]
        st.success(f"✨ 「{s['kw']}」成功獲得 {len(results)} 筆搜尋結果與重點摘要：")
        if s.get("ai_summary"):
            st.subheader("🤖 AI 整體重點")
            with st.container(key="ai_answer"):
                st.markdown(s["ai_summary"])

        export_lines = [f"# 搜尋：{s['kw']}\n"]
        for idx, item in enumerate(results, 1):
            points = summarize_snippet(item['snippet'])
            points_html = "".join([f"<p style='margin:2px 0;'>{esc(pt)}</p>" for pt in points])
            render_html(f"""
            <div class="summary-box">
                <h4 style="margin:0;">{idx}. {esc(item['title'])}</h4>
                <div style="margin: 8px 0;">
                    <b>💡 核心摘要重點：</b>
                    {points_html}
                </div>
                <a href="{safe_href(item['url'])}" target="_blank" rel="noopener noreferrer">🌐 開啟原始網頁連結</a>
            </div>
            """)
            export_lines.append(f"## {idx}. {item['title']}\n" + "\n".join(points) + f"\n\n{item['url']}\n")
        st.download_button(
            "⬇️ 下載搜尋結果 (.md)", "\n".join(export_lines),
            file_name="search_results.md", mime="text/markdown", key="search_dl",
        )


# (2) 🌐 指定網址擷取
def do_fetch(url):
    with st.spinner("正在讀取網頁內文..."):
        try:
            st.session_state.url_result = {"url": url, **fetch_page(url)}
        except Exception as e:
            st.session_state.url_result = {"url": url, "error": str(e)}
            st.toast("網頁讀取失敗", icon="⚠️")


def page_url():
    with main_card():
        st.header("🌐 指定網址文字擷取與重點整理")
        target_url = st.text_input("請輸入目標網址 (包含 http:// 或 https://)：", placeholder="https://example.com", key="url_input")
        filter_text = st.text_input("輸入要篩選的特定關鍵字 (選填，結果會即時篩選並高亮)：", key="url_filter")

        if st.button("擷取網頁內容", key="url_btn"):
            if not valid_url(target_url):
                st.warning("請輸入有效的完整 URL！")
            else:
                do_fetch(target_url.strip())

        r = st.session_state.url_result
        if not r:
            return
        if r.get("error"):
            st.error(f"無法讀取該網址：{r['error']}")
            if st.button("🔁 重試", key="url_retry"):
                do_fetch(r["url"])
                st.rerun()
            return

        paragraphs = r["paragraphs"]
        if filter_text.strip():
            paragraphs = [p for p in paragraphs if filter_text.strip().lower() in p.lower()]
        if not paragraphs:
            st.warning("未找到符合條件的文字內容。")
            return

        st.subheader(f"擷取結果 (共 {len(paragraphs)} 筆重點段落，最多顯示 200 筆)")
        st.caption(f"來源：{r['title']}")
        for idx, text in enumerate(paragraphs[:200], 1):
            render_html(f"""
            <div class="summary-box">
                <b>【段落 {idx}】</b>
                <p style="margin-top:5px;">{highlight(text, filter_text.strip())}</p>
            </div>
            """)
        md = f"# {r['title']}\n\n來源：{r['url']}\n\n" + "\n\n".join(f"- {p}" for p in paragraphs)
        st.download_button("⬇️ 下載擷取內容 (.md)", md, file_name="page_extract.md", mime="text/markdown", key="url_dl")


# (3) 🖼️ 截圖文字辨識
def page_ocr():
    with main_card():
        st.header("🖼️ 截圖文字辨識與關鍵字區域裁切標記")
        uploaded_file = st.file_uploader("上傳截圖 (PNG, JPG, JPEG)：", type=['png', 'jpg', 'jpeg'], key="ocr_upload")
        if uploaded_file is None:
            return

        img_bytes = uploaded_file.getvalue()
        image = ImageOps.exif_transpose(Image.open(io.BytesIO(img_bytes))).convert("RGB")
        st.image(image, caption="原始圖片", use_container_width=True)

        search_target = st.text_input(
            "請輸入要在截圖中搜尋比對的目標關鍵字（多個請用逗號或頓號分隔）：",
            placeholder="例如：確定, 送出, 特定檔名", key="ocr_kw",
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            min_conf = st.slider("最低信心度", 0.0, 1.0, 0.30, 0.05, key="ocr_conf")
        with c2:
            fuzzy_on = st.checkbox("啟用模糊比對", value=True, key="ocr_fuzzy")
        with c3:
            threshold = st.slider("模糊門檻", 0.5, 1.0, 0.75, 0.05, key="ocr_thr", disabled=not fuzzy_on)

        sig = (uploaded_file.name, len(img_bytes))
        if st.button("開始進行 OCR 辨識與視覺定位", key="ocr_btn"):
            st.session_state.ocr_sig = sig
        if st.session_state.ocr_sig != sig:
            return

        with st.spinner("正在進行 OCR 辨識與座標計算（相同圖片會直接使用快取）..."):
            results = run_ocr(img_bytes)
        results = [r for r in results if r[2] >= min_conf]

        st.subheader("📝 提取到的完整文字：")
        st.text_area("OCR 全文內容：", "\n".join(r[1] for r in results), height=120, key="ocr_fulltext")

        keywords = [k.strip().lower() for k in re.split(r"[,，、\n]", search_target) if k.strip()]
        if not keywords:
            return

        annotated_image = image.copy()
        draw = ImageDraw.Draw(annotated_image)
        w, h = image.size
        lw = max(3, int(min(w, h) / 300))
        colors = {"exact": "#00FF66", "partial": "#FFA500", "fuzzy": "#38BDF8"}
        groups = {"exact": [], "partial": [], "fuzzy": []}
        pad = 6

        for bbox, text, prob in results:
            hit = classify(text, keywords, fuzzy_on, threshold)
            if not hit:
                continue
            kind, kw = hit
            xs = [pt[0] for pt in bbox]
            ys = [pt[1] for pt in bbox]
            min_x, max_x, min_y, max_y = int(min(xs)), int(max(xs)), int(min(ys)), int(max(ys))
            draw.rectangle([min_x, min_y, max_x, max_y], outline=colors[kind], width=lw)
            crop_img = image.crop((max(0, min_x - pad), max(0, min_y - pad), min(w, max_x + pad), min(h, max_y + pad)))
            groups[kind].append({"text": text, "prob": prob, "crop": crop_img, "kw": kw})

        st.subheader("🎯 關鍵字定位圖 (綠色：完全符合 | 橘色：部分符合 | 藍色：模糊符合)")
        st.image(annotated_image, caption="標記位置總覽圖", use_container_width=True)
        buf = io.BytesIO()
        annotated_image.save(buf, format="PNG")
        st.download_button("⬇️ 下載標記圖 (PNG)", buf.getvalue(), file_name="annotated.png", mime="image/png", key="ocr_dl")

        st.markdown("---")
        sections = [
            ("exact", "✅ 完全符合結果", "完全對上", "未找到完全一模一樣對上的文字。"),
            ("partial", "🔍 部分符合結果", "部分對上", "未找到包含該關鍵字的部分符合文字。"),
            ("fuzzy", "🔵 模糊符合結果", "模糊對上", "沒有模糊符合的文字。"),
        ]
        for kind, title, label, empty_msg in sections:
            items = groups[kind]
            st.subheader(f"{title} ({len(items)} 筆)")
            if not items:
                st.info(empty_msg)
                continue
            for idx, m in enumerate(items, 1):
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.image(m["crop"], caption=f"{label}區塊 #{idx}", use_container_width=True)
                with col2:
                    render_html(
                        f"<b>【{label} #{idx}】{esc(m['text'])}</b><br>"
                        f"對應關鍵字：「{esc(m['kw'])}」 | 信心度：<b>{m['prob'] * 100:.1f}%</b>"
                    )


# (4) 🧠 自動解題
def page_ai():
    with main_card():
        st.header("🧠 AI 自主解題與文章重點對照定位")
        st.write("自主判讀意圖：支援**題目解答（數學/程式/邏輯）**或**長文搜尋並標註原文句子**。")

        if not st.session_state.api_key:
            st.warning("⚠️ 請先至【⚙️ 設定】頁面填寫 Gemini API Key（或設定環境變數 GEMINI_API_KEY）才能開啟 AI 分析功能！")

        col_input1, col_input2 = st.columns(2)
        with col_input1:
            source_text = st.text_area("📄 貼上文章內文 / 題目文字：", placeholder="輸入文章或題目細節...", height=180, key="ai_text")
        with col_input2:
            uploaded_img = st.file_uploader("📷 上傳題目/文章圖片：", type=['png', 'jpg', 'jpeg'], key="ai_img")
            pil_img = None
            if uploaded_img:
                pil_img = ImageOps.exif_transpose(Image.open(uploaded_img)).convert("RGB")
                pil_img.thumbnail((2048, 2048))
                st.image(pil_img, caption="已上傳題圖", use_container_width=True)

        user_query = st.text_input("💬 輸入指令或問題：", placeholder="例如：「解答這題數學」或「幫我找文章解答在哪一段」", key="ai_query")

        answer_rendered = False
        if st.button("🤖 執行 AI 自主分析與解答", key="ai_btn"):
            if not source_text.strip() and pil_img is None and not user_query.strip():
                st.warning("請至少提供「文字」、「圖片」或「問題指令」！")
            elif not st.session_state.api_key:
                st.error("請先在⚙️ 設定中設定 API Key。")
            else:
                st.markdown("---")
                st.subheader("💡 AI 分析與解答結果：")
                with st.container(key="ai_answer"):
                    st.session_state.ai_answer = st.write_stream(
                        gemini_stream(st.session_state.api_key, get_model(), build_prompt(source_text, user_query), pil_img)
                    )
                answer_rendered = True

        if st.session_state.ai_answer:
            if not answer_rendered:
                st.markdown("---")
                st.subheader("💡 AI 分析與解答結果：")
                with st.container(key="ai_answer"):
                    st.markdown(st.session_state.ai_answer)
            st.download_button(
                "⬇️ 下載解答 (.md)", st.session_state.ai_answer,
                file_name="ai_answer.md", mime="text/markdown", key="ai_dl",
            )


# (5) ⚙️ 設定
def _sync(widget_key, state_key):
    """設定元件的值同步到持久 state 並存檔（頁面切換時元件 key 會被清除，所以不直接用它當資料來源）。"""
    st.session_state[state_key] = st.session_state[widget_key]
    save_settings()


def _on_api_key():
    st.session_state.api_key = st.session_state.api_key_widget
    save_settings()
    st.toast("API Key 已更新", icon="✅")


def page_settings():
    with main_card():
        st.header("⚙️ 系統與介面個人化設定")
        st.write("在此頁面微調軟體的外觀風格與 AI 服務連線金鑰。設定會儲存在本機（`.app_settings.json`），重新整理後不會遺失。")
        if st.session_state.bg_notice:
            st.toast(st.session_state.bg_notice, icon="✅")
            st.session_state.bg_notice = None
        st.markdown("---")

        # A. 介面主題與色彩
        st.subheader("🎨 介面主題與色彩")
        theme_names = list(THEME_CONFIGS.keys())
        st.selectbox(
            "選擇系統主題風格：", theme_names,
            index=theme_names.index(st.session_state.theme_mode),
            key="theme_widget", on_change=_sync, args=("theme_widget", "theme_mode"),
        )
        st.caption("若已上傳自訂背景圖，背景以圖片為主；清除背景圖後即顯示主題底色。")
        st.markdown("---")

        # B. 自訂背景圖
        st.subheader("🖼️ 個人自訂背景圖")
        bg_file = st.file_uploader(
            "選擇上傳您喜愛的桌布圖片 (PNG / JPG / WEBP)：", type=['png', 'jpg', 'jpeg', 'webp'],
            key=f"bg_uploader_{st.session_state.bg_uploader_ver}",
        )
        if bg_file is not None:
            try:
                data = process_bg(bg_file.getvalue())
                BG_PATH.write_bytes(data)
                st.session_state.bg_image_b64 = base64.b64encode(data).decode("utf-8")
                st.session_state.bg_notice = "背景圖已套用"
            except Exception as e:
                st.session_state.bg_notice = f"背景圖處理失敗：{e}"
            st.session_state.bg_uploader_ver += 1  # 重建上傳元件，避免重複套用造成無限 rerun
            st.rerun()
        if st.button("🗑️ 清除自訂背景 (恢復預設背景)", key="bg_clear"):
            st.session_state.bg_image_b64 = None
            BG_PATH.unlink(missing_ok=True)
            st.session_state.bg_uploader_ver += 1
            st.rerun()

        st.markdown("---")

        # C. Gemini API Key / 模型
        st.subheader("🔑 AI 服務連線設定")
        st.text_input(
            "Gemini API Key：", value=st.session_state.api_key, type="password",
            key="api_key_widget", on_change=_on_api_key,
            help="自動解題模式必填；也可用 .streamlit/secrets.toml 的 GEMINI_API_KEY 或同名環境變數。",
        )
        st.checkbox(
            "在本機記住 API Key（明文存於 .app_settings.json，共用電腦請勿勾選）",
            value=st.session_state.remember_key,
            key="remember_widget", on_change=_sync, args=("remember_widget", "remember_key"),
        )
        st.selectbox(
            "AI 模型：", MODEL_OPTIONS, index=MODEL_OPTIONS.index(st.session_state.model_choice)
            if st.session_state.model_choice in MODEL_OPTIONS else 0,
            key="model_widget", on_change=_sync, args=("model_widget", "model_choice"),
        )
        if st.session_state.model_choice == "自訂...":
            st.text_input(
                "自訂模型名稱：", value=st.session_state.custom_model, placeholder="例如：gemini-2.5-flash",
                key="custom_widget", on_change=_sync, args=("custom_widget", "custom_model"),
            )

        if st.button("🔌 測試連線", key="api_test"):
            if not st.session_state.api_key:
                st.warning("請先輸入 API Key。")
            else:
                with st.spinner("測試中..."):
                    reply = gemini_text("請只回覆 OK 兩個字。")
                if reply.startswith("❌"):
                    st.error(reply)
                else:
                    st.success(f"✅ 連線成功（{get_model()}）：{reply.strip()[:40]}")

        st.markdown("[👉 免費申請 Gemini API Key](https://aistudio.google.com/)")


PAGES = {
    "🏠 首頁": page_home,
    "🔍 關鍵字搜尋": page_search,
    "🌐 指定網址擷取": page_url,
    "🖼️ 截圖文字辨識": page_ocr,
    "🧠 自動解題": page_ai,
    "⚙️ 設定": page_settings,
}
PAGES[nav_mode]()