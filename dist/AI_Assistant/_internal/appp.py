import streamlit as st
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw
import easyocr
import numpy as np
import urllib.parse
import re
import base64
import io

# 1. 頁面基本設定 (隱藏預設側邊欄)
st.set_page_config(
    page_title="🤖 智慧資訊擷取與 AI 輔助系統",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------------------------
# 2. HTML 渲染終極修正函數 (徹底消除每行開頭空格，防 Markdown 誤判)
# -------------------------------------------------------------------
def render_html(html_str):
    clean_str = "\n".join(line.strip() for line in html_str.splitlines())
    st.markdown(clean_str, unsafe_allow_html=True)

# -------------------------------------------------------------------
# 3. Session 狀態初始化
# -------------------------------------------------------------------
if "bg_image_b64" not in st.session_state:
    st.session_state.bg_image_b64 = None
if "main_theme" not in st.session_state:
    st.session_state.main_theme = "純黑模式 (Dark Black)"
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

# -------------------------------------------------------------------
# 4. 動態 CSS 注入 (背景清晰透圖 + 文字卡片不透明強化)
# -------------------------------------------------------------------
bg_css = f"""
    background-image: url("data:image/jpeg;base64,{st.session_state.bg_image_b64}");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
""" if st.session_state.bg_image_b64 else "background-color: #0b0f19;"

render_html(f"""
<style>
    /* 完全隱藏預設側邊欄 */
    section[data-testid="stSidebar"] {{
        display: none !important;
    }}

    /* 全域背景 */
    .stApp {{
        {bg_css}
    }}

    /* 頂部選單容器 */
    div[data-testid="stRadio"] > div[role="radiogroup"] {{
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        gap: 20px !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 10px 0 20px 0 !important;
    }}

    /* 隱藏 Radio 原生圓圈與圖示 */
    div[data-testid="stRadio"] input[type="radio"],
    div[data-testid="stRadio"] label > div:first-child,
    div[data-testid="stRadio"] label svg {{
        display: none !important;
        width: 0 !important;
        height: 0 !important;
        opacity: 0 !important;
    }}

    /* 個別頂部選單按鈕 */
    div[data-testid="stRadio"] label {{
        background: rgba(15, 23, 42, 0.75) !important;
        backdrop-filter: blur(8px) !important;
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
        border-radius: 16px !important;
        padding: 12px 26px !important;
        cursor: pointer !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3) !important;
        transition: all 0.3s ease !important;
        margin: 0 !important;
    }}

    /* 頂部選單內部文字 */
    div[data-testid="stRadio"] label *,
    div[data-testid="stRadio"] label p,
    div[data-testid="stRadio"] label span {{
        color: #ffffff !important;
        font-size: 19px !important;
        font-weight: 700 !important;
        margin: 0 !important;
    }}

    /* 上下跳動 Keyframes */
    @keyframes hoverBounce {{
        0%, 100% {{ transform: translateY(0px) scale(1.06); }}
        50% {{ transform: translateY(-8px) scale(1.06); }}
    }}

    /* 選單懸停 (Hover) */
    div[data-testid="stRadio"] label:hover {{
        background: rgba(255, 255, 255, 0.25) !important;
        border-color: #ffffff !important;
        animation: hoverBounce 1s infinite ease-in-out !important;
        box-shadow: 0 10px 25px rgba(255, 255, 255, 0.3) !important;
    }}

    /* 當前選中的功能頁面 (Active) */
    div[data-testid="stRadio"] label:has(input:checked) {{
        background: #ffffff !important;
        border-color: #ffffff !important;
        box-shadow: 0 10px 28px rgba(255, 255, 255, 0.5) !important;
        transform: translateY(-4px) scale(1.06) !important;
    }}

    div[data-testid="stRadio"] label:has(input:checked) *,
    div[data-testid="stRadio"] label:has(input:checked) p,
    div[data-testid="stRadio"] label:has(input:checked) span {{
        color: #0f172a !important;
    }}

    /* -------------------------------------------------------------- */
    /* 主外框面板：高透明度 + 超微弱模糊，背景底圖清晰可見 */
    /* -------------------------------------------------------------- */
    .main-card {{
        background: rgba(15, 23, 42, 0.22) !important;
        backdrop-filter: blur(3px) !important;
        -webkit-backdrop-filter: blur(3px) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 24px !important;
        padding: 36px !important;
        margin-bottom: 25px !important;
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.35) !important;
        color: #f8fafc !important;
    }}

    /* 動態藍紫科技光束分割線 */
    @keyframes cyberGlow {{
        0% {{ background-position: 0% 50%; }}
        50% {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
    }}
    .cyber-line {{
        height: 2px;
        width: 100%;
        background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc, #38bdf8);
        background-size: 200% 200%;
        animation: cyberGlow 4s infinite ease;
        margin: 24px 0;
        border-radius: 2px;
    }}

    /* 動態呼吸燈訊號 */
    @keyframes pulseGlow {{
        0% {{ box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7); transform: scale(1); }}
        70% {{ box-shadow: 0 0 0 10px rgba(34, 197, 94, 0); transform: scale(1.1); }}
        100% {{ box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); transform: scale(1); }}
    }}
    .pulse-dot {{
        display: inline-block;
        width: 12px;
        height: 12px;
        background-color: #22c55e;
        border-radius: 50%;
        margin-right: 8px;
        animation: pulseGlow 2s infinite;
    }}

    /* 科技感數據儀表網格 */
    .tech-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 18px;
        margin: 20px 0;
    }}

    /* -------------------------------------------------------------- */
    /* 文字卡片：加深不透明底色 (Alpha 0.8)，確保文字極度清晰易讀 */
    /* -------------------------------------------------------------- */
    .tech-card {{
        background: rgba(15, 23, 42, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.18) !important;
        backdrop-filter: blur(12px) !important;
        border-radius: 16px;
        padding: 20px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3);
    }}
    .tech-card:hover {{
        background: rgba(15, 23, 42, 0.9) !important;
        border-color: rgba(56, 189, 248, 0.6) !important;
        transform: translateY(-5px);
        box-shadow: 0 12px 28px rgba(0, 0, 0, 0.5);
    }}

    /* 摘要文字外框區塊 */
    .summary-box {{
        background-color: rgba(15, 23, 42, 0.85) !important;
        border-left: 4px solid #c084fc;
        padding: 16px 20px;
        border-radius: 12px;
        margin: 14px 0;
        backdrop-filter: blur(10px);
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.3);
    }}

    /* 輸入框黑底不透明化，防止文字重疊背景 */
    .stTextInput input, .stTextArea textarea {{
        background-color: rgba(15, 23, 42, 0.85) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }}
</style>
""")

# -------------------------------------------------------------------
# 5. 頂部導覽列
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
# 6. 工具函數 (OCR / 搜尋 / AI)
# -------------------------------------------------------------------
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['ch_tra', 'en'])

def summarize_snippet(text):
    text = re.sub(r'\s+', ' ', text).strip()
    sentences = [s.strip() for s in re.split(r'[。！!？?\n]', text) if len(s.strip()) > 5]
    if not sentences:
        return ["• " + text] if text else ["• 暫無詳細摘要重點。"]
    return ["• " + s for s in sentences[:3]]

def fetch_search_results(kw, max_results=8):
    results = []
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            ddg_res = list(ddgs.text(kw, max_results=max_results))
            for r in ddg_res:
                results.append({'title': r.get('title', ''), 'url': r.get('href', ''), 'snippet': r.get('body', '')})
        if results:
            return results
    except Exception:
        pass

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
            if results:
                return results
    except Exception:
        pass

    return results

def ask_gemini(key, prompt_text, pil_image=None):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
    parts = []
    if pil_image is not None:
        buffered = io.BytesIO()
        pil_image.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": img_str
            }
        })
    parts.append({"text": prompt_text})
    payload = {"contents": [{"parts": parts}]}
    headers = {"Content-Type": "application/json"}
    
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    if response.status_code == 200:
        data = response.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            return "❌ 無法解析 AI 回傳的資料結構。"
    else:
        return f"❌ API 請求失敗 (HTTP Status: {response.status_code}):\n{response.text}"

# -------------------------------------------------------------------
# 7. 主功能面板區域
# -------------------------------------------------------------------

# (0) 🏠 首頁
if nav_mode == "🏠 首頁":
    bg_status = "已載入個人視覺化桌布" if st.session_state.bg_image_b64 else "預設深色星空底圖"
    api_status = "ONLINE (已連線)" if st.session_state.api_key else "OFFLINE (請至⚙️ 設定配置)"
    api_color = "#22c55e" if st.session_state.api_key else "#f43f5e"

    render_html(f"""
    <div class="main-card">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <div>
                <h1 style="margin: 0; font-size: 32px; font-weight: 800; background: linear-gradient(90deg, #38bdf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                    🤖 智慧資訊擷取與 AI 輔助系統
                </h1>
                <p style="margin-top: 6px; color: #cbd5e1; font-size: 16px; font-weight: 600;">Next-Gen Intelligence & Multimodal Analytics Portal</p>
            </div>
            <div style="background: rgba(15, 23, 42, 0.8); padding: 8px 18px; border-radius: 30px; border: 1px solid rgba(56, 189, 248, 0.4); display: flex; align-items: center;">
                <span class="pulse-dot"></span>
                <span style="font-weight: 700; font-size: 14px; color: #38bdf8;">SYSTEM READY</span>
            </div>
        </div>

        <div class="cyber-line"></div>

        <h3 style="color:#ffffff; margin-top:0; text-shadow: 0 2px 4px rgba(0,0,0,0.8);">⚡ 系統核心即時狀態 (Live System Status)</h3>
        <div class="tech-grid">
            <div class="tech-card">
                <div style="font-size: 13px; color: #94a3b8; font-weight: 600;">🖼️ 個人化視覺背景</div>
                <div style="font-size: 18px; font-weight: 700; margin-top: 8px; color: #38bdf8;">{bg_status}</div>
            </div>
            <div class="tech-card">
                <div style="font-size: 13px; color: #94a3b8; font-weight: 600;">🔑 AI 引擎狀態</div>
                <div style="font-size: 18px; font-weight: 700; margin-top: 8px; color: {api_color};">{api_status}</div>
            </div>
            <div class="tech-card">
                <div style="font-size: 13px; color: #94a3b8; font-weight: 600;">🎨 面板質感風格</div>
                <div style="font-size: 18px; font-weight: 700; margin-top: 8px; color: #c084fc;">全景高透光 + 文字清晰黑框</div>
            </div>
        </div>

        <div class="cyber-line"></div>

        <h3 style="color:#ffffff; text-shadow: 0 2px 4px rgba(0,0,0,0.8);">🚀 模組化功能導向 (Functional Modules)</h3>
        <div class="tech-grid">
            <div class="tech-card">
                <h4 style="margin: 0; color: #38bdf8;">🔍 關鍵字精準搜尋</h4>
                <p style="font-size: 14px; color: #e2e8f0; margin-top: 8px;">即時聯網檢索，自動提取網頁核心重點並條列化濃縮。</p>
            </div>
            <div class="tech-card">
                <h4 style="margin: 0; color: #38bdf8;">🌐 指定網址擷取</h4>
                <p style="font-size: 14px; color: #e2e8f0; margin-top: 8px;">智慧解析目標網站段落結構，支援關鍵字精準篩選。</p>
            </div>
            <div class="tech-card">
                <h4 style="margin: 0; color: #c084fc;">🖼️ 截圖文字辨識</h4>
                <p style="font-size: 14px; color: #e2e8f0; margin-top: 8px;">EasyOCR 多國語言辨識，精準黃/綠框標記區域與自動裁切。</p>
            </div>
            <div class="tech-card">
                <h4 style="margin: 0; color: #c084fc;">🧠 自動解題與推理</h4>
                <p style="font-size: 14px; color: #e2e8f0; margin-top: 8px;">Gemini 2.5 多模態 AI，自動識別題型、邏輯推導與原文句子定位。</p>
            </div>
        </div>
    </div>
    """)

# (1) 🔍 關鍵字搜尋
elif nav_mode == "🔍 關鍵字搜尋":
    render_html('<div class="main-card">')
    st.header("🔍 關鍵字精準搜尋與智慧重點濃縮")
    keyword = st.text_input("請輸入搜尋關鍵字：", placeholder="例如：最新 AI 發展趨勢")
    
    if st.button("開始搜尋與濃縮"):
        if not keyword.strip():
            st.warning("請先輸入關鍵字！")
        else:
            with st.spinner(f"正在搜尋並濃縮「{keyword}」..."):
                search_results = fetch_search_results(keyword, max_results=8)
                if not search_results:
                    st.error("❌ 暫時無法連線至搜尋服務，請稍後再試。")
                else:
                    st.success(f"✨ 成功獲得 {len(search_results)} 筆搜尋結果與重點摘要：")
                    for idx, item in enumerate(search_results, 1):
                        points = summarize_snippet(item['snippet'])
                        points_html = "".join([f"<p style='margin:2px 0;'>{pt}</p>" for pt in points])
                        render_html(f"""
                        <div class="summary-box">
                            <h4 style="margin:0; color:#38bdf8;">{idx}. {item['title']}</h4>
                            <div style="margin: 8px 0;">
                                <b>💡 核心摘要重點：</b>
                                {points_html}
                            </div>
                            <a href="{item['url']}" target="_blank" style="color:#c084fc;">🌐 開啟原始網頁連結</a>
                        </div>
                        """)
    render_html('</div>')

# (2) 🌐 指定網址擷取
elif nav_mode == "🌐 指定網址擷取":
    render_html('<div class="main-card">')
    st.header("🌐 指定網址文字擷取與重點整理")
    target_url = st.text_input("請輸入目標網址 (包含 http:// 或 https://)：", placeholder="https://example.com")
    filter_text = st.text_input("輸入要篩選的特定關鍵字 (選填)：")
    
    if st.button("擷取網頁內容"):
        if not target_url.strip().startswith("http"):
            st.warning("請輸入有效的完整 URL！")
        else:
            with st.spinner("正在讀取網頁內文..."):
                headers = {"User-Agent": "Mozilla/5.0"}
                try:
                    res = requests.get(target_url, headers=headers, timeout=10)
                    res.encoding = 'utf-8'
                    soup = BeautifulSoup(res.text, 'html.parser')
                    paragraphs = [p.get_text().strip() for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'li']) if len(p.get_text().strip()) > 10]
                    
                    if filter_text:
                        paragraphs = [p for p in paragraphs if filter_text.lower() in p.lower()]
                    
                    if paragraphs:
                        st.subheader(f"擷取結果 (共 {len(paragraphs)} 筆重點段落)")
                        for idx, text in enumerate(paragraphs, 1):
                            render_html(f"""
                            <div class="summary-box">
                                <b>【段落 {idx}】</b>
                                <p style="margin-top:5px;">{text}</p>
                            </div>
                            """)
                    else:
                        st.warning("未找到符合條件的文字內容。")
                except Exception as e:
                    st.error(f"無法讀取該網址：{e}")
    render_html('</div>')

# (3) 🖼️ 截圖文字辨識
elif nav_mode == "🖼️ 截圖文字辨識":
    render_html('<div class="main-card">')
    st.header("🖼️ 截圖文字辨識與關鍵字區域裁切標記")
    uploaded_file = st.file_uploader("上傳截圖 (PNG, JPG, JPEG)：", type=['png', 'jpg', 'jpeg'])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file).convert("RGB")
        st.image(image, caption="原始圖片", use_container_width=True)
        search_target = st.text_input("請輸入要在截圖中搜尋比對的目標關鍵字：", placeholder="例如：確定 / 送出 / 特定檔名")
        
        if st.button("開始進行 OCR 辨識與視覺定位"):
            with st.spinner("正在進行 OCR 辨識與座標計算..."):
                reader = load_ocr()
                img_array = np.array(image)
                results = reader.readtext(img_array)
                
                extracted_texts = [res[1] for res in results]
                full_text = "\n".join(extracted_texts)
                
                st.subheader("📝 提取到的完整文字：")
                st.text_area("OCR 全文內容：", full_text, height=120)
                
                if search_target.strip():
                    target_clean = search_target.strip().lower()
                    exact_matches = []
                    partial_matches = []
                    
                    annotated_image = image.copy()
                    draw = ImageDraw.Draw(annotated_image)
                    w, h = image.size
                    
                    for bbox, text, prob in results:
                        text_clean = text.strip().lower()
                        xs = [pt[0] for pt in bbox]
                        ys = [pt[1] for pt in bbox]
                        min_x, max_x = int(min(xs)), int(max(xs))
                        min_y, max_y = int(min(ys)), int(max(ys))
                        
                        pad = 6
                        crop_box = (
                            max(0, min_x - pad),
                            max(0, min_y - pad),
                            min(w, max_x + pad),
                            min(h, max_y + pad)
                        )
                        crop_img = image.crop(crop_box)
                        
                        item_data = {"text": text, "prob": prob, "crop": crop_img}
                        
                        if text_clean == target_clean:
                            exact_matches.append(item_data)
                            draw.rectangle([min_x, min_y, max_x, max_y], outline="#00FF66", width=4)
                        elif target_clean in text_clean:
                            partial_matches.append(item_data)
                            draw.rectangle([min_x, min_y, max_x, max_y], outline="#FFA500", width=3)
                    
                    st.subheader("🎯 關鍵字定位圖 (綠色：完全符合 | 橘色：部分符合)")
                    st.image(annotated_image, caption="標記位置總覽圖", use_container_width=True)
                    
                    st.markdown("---")
                    st.subheader(f"✅ 完全符合結果 ({len(exact_matches)} 筆)")
                    if exact_matches:
                        for idx, match in enumerate(exact_matches, 1):
                            col1, col2 = st.columns([1, 3])
                            with col1:
                                st.image(match["crop"], caption=f"完全符合區塊 #{idx}", use_container_width=True)
                            with col2:
                                render_html(f"<b>【完全對上 #{idx}】{match['text']}</b><br>信心度：<b>{match['prob']*100:.1f}%</b>")
                    else:
                        st.info("未找到完全一模一樣對上的文字。")
                    
                    st.subheader(f"🔍 部分符合結果 ({len(partial_matches)} 筆)")
                    if partial_matches:
                        for idx, match in enumerate(partial_matches, 1):
                            col1, col2 = st.columns([1, 3])
                            with col1:
                                st.image(match["crop"], caption=f"部分符合區塊 #{idx}", use_container_width=True)
                            with col2:
                                render_html(f"<b>【部分對上 #{idx}】{match['text']}</b><br>包含關鍵字：「{search_target}」 | 信心度：<b>{match['prob']*100:.1f}%</b>")
                    else:
                        st.info("未找到包含該關鍵字的部分符合文字。")
    render_html('</div>')

# (4) 🧠 自動解題
elif nav_mode == "🧠 自動解題":
    render_html('<div class="main-card">')
    st.header("🧠 AI 自主解題與文章重點對照定位")
    st.write("自主判讀意圖：支援**題目解答（數學/程式/邏輯）**或**長文搜尋並標註原文句子**。")
    
    if not st.session_state.api_key:
        st.warning("⚠️ 請先至【⚙️ 設定】頁面填寫 Gemini API Key 才能開啟 AI 分析功能！")
    
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        source_text = st.text_area("📄 貼上文章內文 / 題目文字：", placeholder="輸入文章或題目細節...", height=180)
    with col_input2:
        uploaded_img = st.file_uploader("📷 上傳題目/文章圖片：", type=['png', 'jpg', 'jpeg'])
        if uploaded_img:
            img_preview = Image.open(uploaded_img)
            st.image(img_preview, caption="已上傳題圖", use_container_width=True)

    user_query = st.text_input("💬 輸入指令或問題：", placeholder="例如：「解答這題數學」或「幫我找文章解答在哪一段」")

    if st.button("🤖 執行 AI 自主分析與解答"):
        if not source_text.strip() and uploaded_img is None and not user_query.strip():
            st.warning("請至少提供「文字」、「圖片」或「問題指令」！")
        elif not st.session_state.api_key:
            st.error("請先在⚙️ 設定中設定 API Key。")
        else:
            with st.spinner("🧠 AI 正在進行自主分析與邏輯推導..."):
                pil_img = Image.open(uploaded_img).convert("RGB") if uploaded_img else None
                
                system_prompt = f"""
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
                ai_response = ask_gemini(st.session_state.api_key, system_prompt, pil_img)
                
                st.markdown("---")
                st.subheader("💡 AI 分析與解答結果：")
                render_html(f'<div class="summary-box">{ai_response}</div>')
    render_html('</div>')

# (5) ⚙️ 設定
elif nav_mode == "⚙️ 設定":
    render_html('<div class="main-card">')
    st.header("⚙️ 系統與介面個人化設定")
    st.write("在此頁面微調軟體的外觀風格與 AI 服務連線金鑰。")
    st.markdown("---")

    # A. 自訂背景圖
    st.subheader("🖼️ 個人自訂背景圖")
    bg_file = st.file_uploader("選擇上傳您喜愛的桌布圖片 (PNG / JPG / WEBP)：", type=['png', 'jpg', 'jpeg', 'webp'])
    col_bg1, col_bg2 = st.columns([1, 4])
    with col_bg1:
        if bg_file is not None:
            bg_bytes = bg_file.read()
            st.session_state.bg_image_b64 = base64.b64encode(bg_bytes).decode('utf-8')
            st.success("✅ 背景圖已套用！")
            st.rerun()
    with col_bg2:
        if st.button("🗑️ 清除自訂背景 (恢復預設背景)"):
            st.session_state.bg_image_b64 = None
            st.rerun()

    st.markdown("---")

    # B. Gemini API Key
    st.subheader("🔑 AI 服務連線設定")
    new_api_key = st.text_input(
        "Gemini API Key：", 
        value=st.session_state.api_key,
        type="password", 
        help="自動解題模式必填"
    )
    if new_api_key != st.session_state.api_key:
        st.session_state.api_key = new_api_key
        st.success("✅ API Key 已更新！")

    st.markdown("[👉 免費申請 Gemini API Key](https://aistudio.google.com/)")
    render_html('</div>')