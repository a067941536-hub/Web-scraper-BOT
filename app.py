import streamlit as st
import requests
from bs4 import BeautifulSoup
from PIL import Image
import easyocr
import numpy as np

# 設定頁面標題與圖示
st.set_page_config(page_title="多功能網絡與圖片資訊擷取機器人", page_icon="🤖", layout="wide")

st.title("🤖 多功能網絡與圖片資訊擷取機器人")
st.caption("支援關鍵字搜尋、網址特定內容擷取與截圖 OCR 文字辨識")

# 側邊欄切換模式
mode = st.sidebar.radio(
    "請選擇功能模式：",
    ["1. 關鍵字搜尋", "2. 指定網址文字擷取", "3. 圖片/截圖文字辨識 (OCR)"]
)

# Initialize EasyOCR reader (cached to prevent re-loading)
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['ch_tra', 'en'])

# -------------------------------------------------------------------
# 模式 1：關鍵字搜尋
# -------------------------------------------------------------------
if mode == "1. 關鍵字搜尋":
    st.header("🔍 模式 1：關鍵字搜尋")
    keyword = st.text_input("請輸入要搜尋的關鍵字：", placeholder="例如：人工智能 最新趨勢")
    num_results = st.slider("想要擷取的結果數量：", 3, 15, 5)
    
    if st.button("開始搜尋"):
        if not keyword.strip():
            st.warning("請先輸入關鍵字！")
        else:
            with st.spinner("搜尋中..."):
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                url = f"https://html.duckduckgo.com/html/?q={keyword}"
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    results = soup.find_all('a', class_='result__url', limit=num_results)
                    titles = soup.find_all('a', class_='result__a', limit=num_results)
                    snippets = soup.find_all('a', class_='result__snippet', limit=num_results)
                    
                    if not titles:
                        st.error("未找到相關結果或遭遇請求限制。")
                    else:
                        st.success(f"成功找到 {len(titles)} 筆結果：")
                        for idx, (t, s) in enumerate(zip(titles, snippets), 1):
                            st.markdown(f"### {idx}. {t.get_text()}")
                            st.write(s.get_text())
                            st.markdown(f"[點擊造訪連結]({t['href']})")
                            st.divider()
                except Exception as e:
                    st.error(f"搜尋過程發生錯誤：{e}")

# -------------------------------------------------------------------
# 模式 2：指定網址文字擷取
# -------------------------------------------------------------------
elif mode == "2. 指定網址文字擷取":
    st.header("🌐 模式 2：指定網址文字擷取")
    target_url = st.text_input("請輸入目標網址 (包含 http:// 或 https://)：", placeholder="https://example.com")
    filter_text = st.text_input("輸入要篩選的特定關鍵字或標籤 (選填)：", placeholder="例如：價格 / 標題 / 優惠")
    
    if st.button("擷取網頁內容"):
        if not target_url.strip():
            st.warning("請輸入有效的網址！")
        else:
            with st.spinner("正在讀取網頁..."):
                headers = {"User-Agent": "Mozilla/5.0"}
                try:
                    res = requests.get(target_url, headers=headers, timeout=10)
                    res.encoding = 'utf-8'
                    soup = BeautifulSoup(res.text, 'html.parser')
                    
                    # 抓取段落與標題
                    paragraphs = [p.get_text().strip() for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'li']) if p.get_text().strip()]
                    
                    if filter_text:
                        paragraphs = [p for p in paragraphs if filter_text.lower() in p.lower()]
                    
                    st.subheader(f"擷取結果 (共 {len(paragraphs)} 筆符合內容)")
                    if paragraphs:
                        for idx, text in enumerate(paragraphs, 1):
                            st.info(f"**[{idx}]** {text}")
                    else:
                        st.warning("未找到符合篩選條件的文字內容。")
                except Exception as e:
                    st.error(f"無法讀取該網址：{e}")

# -------------------------------------------------------------------
# 模式 3：圖片/截圖文字辨識 (OCR)
# -------------------------------------------------------------------
elif mode == "3. 圖片/截圖文字辨識 (OCR)":
    st.header("🖼️ 模式 3：圖片/截圖文字辨識")
    uploaded_file = st.file_uploader("請上傳需要辨識的截圖 (PNG, JPG, JPEG)：", type=['png', 'jpg', 'jpeg'])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="已上傳圖片", use_column_width=True)
        
        search_target = st.text_input("請輸入要在截圖中比對的目標文字 (選填)：")
        
        if st.button("開始進行 OCR 辨識"):
            with st.spinner("辨識圖片文字中（首次執行需要載入模型）..."):
                reader = load_ocr()
                img_array = np.array(image)
                results = reader.readtext(img_array)
                
                extracted_texts = [res[1] for res in results]
                full_text = "\n".join(extracted_texts)
                
                st.subheader("📝 辨識完整結果：")
                st.text_area("提取文字內容：", full_text, height=200)
                
                if search_target:
                    matched = [t for t in extracted_texts if search_target.lower() in t.lower()]
                    st.subheader("🎯 目標文字匹配結果：")
                    if matched:
                        for m in matched:
                            st.success(f"找到匹配項目：{m}")
                    else:
                        st.warning(f"未在截圖中找到包含「{search_target}」的文字。")