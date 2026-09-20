import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import requests
from bs4 import BeautifulSoup
from PIL import Image
import easyocr
import numpy as np
import os
import webbrowser
import urllib.parse
import re

# ================= 顏色與主題設定 (夢幻紫色調) =================
COLOR_MAIN_BG = "#130E1E"       # 深暗紫背景
COLOR_SIDEBAR_BG = "#1C142A"    # 側邊欄背景
COLOR_CARD_BG = "#261C3B"       # 卡片背景
COLOR_CARD_HOVER = "#32244C"    # 卡片懸停色
COLOR_ACCENT = "#9333EA"        # 主紫霓虹色
COLOR_ACCENT_HOVER = "#A855F7"  # 按鈕懸停紫
COLOR_TEXT_BRIGHT = "#F3E8FF"   # 亮紫色字體
COLOR_TEXT_MUTED = "#C0B2D6"    # 淡紫輔助字體
COLOR_BORDER = "#583A85"        # 紫色邊框
COLOR_HIGHLIGHT = "#3B2554"     # 重點背景色

ctk.set_appearance_mode("Dark")

class DreamyPurpleApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("✨ 夢幻紫多功能爬蟲與資訊擷取助理 v2.1")
        self.geometry("1080x720")
        self.minsize(900, 600)
        self.configure(fg_color=COLOR_MAIN_BG)

        self.ocr_reader = None
        self.selected_image_path = None

        # 網格佈局 (側邊欄 + 主內容)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ================= 側邊欄 =================
        self.sidebar_frame = ctk.CTkFrame(self, width=220, fg_color=COLOR_SIDEBAR_BG, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="✨ 爬蟲助理", 
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLOR_TEXT_BRIGHT
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(25, 20))

        # 選單按鈕
        self.btn_mode1 = self.create_sidebar_btn("🔍 關鍵字精準搜尋", self.show_mode1)
        self.btn_mode1.grid(row=1, column=0, padx=15, pady=8)

        self.btn_mode2 = self.create_sidebar_btn("🌐 網址文字濃縮", self.show_mode2)
        self.btn_mode2.grid(row=2, column=0, padx=15, pady=8)

        self.btn_mode3 = self.create_sidebar_btn("🖼️ 截圖辨識 (OCR)", self.show_mode3)
        self.btn_mode3.grid(row=3, column=0, padx=15, pady=8)

        # ================= 主內容面板 =================
        self.frame_mode1 = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_mode2 = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_mode3 = ctk.CTkFrame(self, fg_color="transparent")

        self.setup_mode1_ui()
        self.setup_mode2_ui()
        self.setup_mode3_ui()

        self.show_mode1()

    def create_sidebar_btn(self, text, command):
        return ctk.CTkButton(
            self.sidebar_frame,
            text=text,
            command=command,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            corner_radius=10
        )

    def hide_all_frames(self):
        self.frame_mode1.grid_forget()
        self.frame_mode2.grid_forget()
        self.frame_mode3.grid_forget()

    def show_mode1(self):
        self.hide_all_frames()
        self.frame_mode1.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

    def show_mode2(self):
        self.hide_all_frames()
        self.frame_mode2.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

    def show_mode3(self):
        self.hide_all_frames()
        self.frame_mode3.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

    # ================= 模式 1：關鍵字精準搜尋 (多重備援搜尋引擎) =================
    def setup_mode1_ui(self):
        self.frame_mode1.grid_columnconfigure(0, weight=1)
        self.frame_mode1.grid_rowconfigure(2, weight=1)

        # 頂部搜尋區
        top_bar = ctk.CTkFrame(self.frame_mode1, fg_color=COLOR_CARD_BG, corner_radius=12)
        top_bar.grid(row=0, column=0, padx=0, pady=(0, 15), sticky="ew")
        top_bar.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(top_bar, text="🔍 模式 1：關鍵字精準搜尋與智慧重點濃縮", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_BRIGHT)
        title.grid(row=0, column=0, padx=15, pady=(12, 5), sticky="w")

        input_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        input_frame.grid(row=1, column=0, padx=15, pady=(5, 12), sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)

        self.kw_entry = ctk.CTkEntry(input_frame, placeholder_text="請輸入搜尋關鍵字 (例如：蛋 / 人工智慧)", fg_color=COLOR_MAIN_BG, text_color=COLOR_TEXT_BRIGHT, border_color=COLOR_BORDER, height=38)
        self.kw_entry.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        btn_search = ctk.CTkButton(input_frame, text="開始搜尋與濃縮", command=self.run_mode1_thread, fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER, height=38, font=ctk.CTkFont(weight="bold"))
        btn_search.grid(row=0, column=1)

        # 結果卡片滾動區
        self.scroll_mode1 = ctk.CTkScrollableFrame(self.frame_mode1, fg_color="transparent")
        self.scroll_mode1.grid(row=2, column=0, sticky="nsew")
        self.scroll_mode1.grid_columnconfigure(0, weight=1)

    def run_mode1_thread(self):
        threading.Thread(target=self.logic_mode1, daemon=True).start()

    def summarize_snippet(self, text):
        """ 清理並提煉關鍵字重點 """
        text = re.sub(r'\s+', ' ', text).strip()
        sentences = [s.strip() for s in re.split(r'[。！!？?\n]', text) if len(s.strip()) > 5]
        
        if not sentences:
            return ["• " + text] if text else ["• 暫無詳細摘要重點。"]
        
        # 濃縮成最多 3 句重點 bullet points
        points = ["• " + s for s in sentences[:3]]
        return points

    def fetch_search_results(self, kw, max_results=8):
        """ 多重引擎自動備援搜尋機制 """
        results = []

        # --- 策略 A: duckduckgo_search API 封裝 (穩定度最高) ---
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                ddg_res = list(ddgs.text(kw, max_results=max_results))
                for r in ddg_res:
                    results.append({
                        'title': r.get('title', ''),
                        'url': r.get('href', ''),
                        'snippet': r.get('body', '')
                    })
            if results:
                return results
        except Exception:
            pass

        # --- 策略 B: Yahoo 奇摩搜尋 (繁體中文極度友好，不會被 Block) ---
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            }
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
                    
                    # 尋找摘要
                    parent = item.find_parent('li') or item.parent
                    snippet_elem = parent.find('div', class_='compText') or parent.find('p') if parent else None
                    snippet = snippet_elem.get_text().strip() if snippet_elem else title
                    
                    if title and href:
                        results.append({
                            'title': title,
                            'url': href,
                            'snippet': snippet
                        })
                if results:
                    return results
        except Exception:
            pass

        # --- 策略 C: DuckDuckGo Lite POST 通道 ---
        try:
            url = "https://lite.duckduckgo.com/lite/"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            res = requests.post(url, data={"q": kw}, headers=headers, timeout=8)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                links = soup.find_all('a', class_='result-link')
                snippets = soup.find_all('td', class_='result-snippet')
                
                for i in range(min(len(links), max_results)):
                    t = links[i].get_text().strip()
                    u = links[i].get('href', '')
                    s = snippets[i].get_text().strip() if i < len(snippets) else t
                    if u.startswith('//'):
                        u = 'https:' + u
                    if t and u:
                        results.append({'title': t, 'url': u, 'snippet': s})
                if results:
                    return results
        except Exception:
            pass

        return results

    def logic_mode1(self):
        kw = self.kw_entry.get().strip()
        if not kw:
            messagebox.showwarning("提示", "請輸入關鍵字！")
            return

        # 清空舊結果
        for child in self.scroll_mode1.winfo_children():
            child.destroy()

        loading_lbl = ctk.CTkLabel(self.scroll_mode1, text=f"✨ 正在搜尋並為您畫重點濃縮「{kw}」...", font=ctk.CTkFont(size=15), text_color=COLOR_TEXT_MUTED)
        loading_lbl.pack(pady=20)

        # 執行多重搜尋機制
        search_results = self.fetch_search_results(kw, max_results=8)
        
        loading_lbl.destroy()

        if not search_results:
            ctk.CTkLabel(self.scroll_mode1, text="❌ 暫時無法連線至搜尋服務，請檢查網路連線或稍後再試。", text_color="#FF6B6B", font=ctk.CTkFont(size=14)).pack(pady=20)
            return

        for idx, item in enumerate(search_results, 1):
            title_text = item['title']
            real_url = item['url']
            snippet_text = item['snippet']

            # 建立卡片 UI
            card = ctk.CTkFrame(self.scroll_mode1, fg_color=COLOR_CARD_BG, border_color=COLOR_BORDER, border_width=1, corner_radius=12)
            card.pack(fill="x", pady=8, padx=5)
            card.grid_columnconfigure(0, weight=1)

            # 標題
            lbl_title = ctk.CTkLabel(card, text=f"{idx}. {title_text}", font=ctk.CTkFont(size=16, weight="bold"), text_color=COLOR_TEXT_BRIGHT, anchor="w", justify="left")
            lbl_title.grid(row=0, column=0, padx=15, pady=(12, 5), sticky="w")

            # 濃縮重點區
            points = self.summarize_snippet(snippet_text)
            summary_box = ctk.CTkFrame(card, fg_color=COLOR_HIGHLIGHT, corner_radius=8)
            summary_box.grid(row=1, column=0, padx=15, pady=5, sticky="ew")

            ctk.CTkLabel(summary_box, text="💡 核心摘要重點：", font=ctk.CTkFont(size=12, weight="bold"), text_color="#E9D5FF").pack(anchor="w", padx=10, pady=(6, 2))
            for pt in points:
                ctk.CTkLabel(summary_box, text=pt, font=ctk.CTkFont(size=13), text_color=COLOR_TEXT_MUTED, anchor="w", justify="left", wraplength=700).pack(anchor="w", padx=15, pady=2)

            # 網址與開啟按鈕
            link_bar = ctk.CTkFrame(card, fg_color="transparent")
            link_bar.grid(row=2, column=0, padx=15, pady=(5, 12), sticky="ew")
            link_bar.grid_columnconfigure(0, weight=1)

            lbl_url = ctk.CTkLabel(link_bar, text=real_url, font=ctk.CTkFont(size=11), text_color="#A78BFA", anchor="w")
            lbl_url.grid(row=0, column=0, sticky="w")

            btn_open = ctk.CTkButton(
                link_bar, 
                text="🌐 開啟網頁", 
                width=90, 
                height=28, 
                fg_color=COLOR_ACCENT, 
                hover_color=COLOR_ACCENT_HOVER,
                command=lambda u=real_url: webbrowser.open(u)
            )
            btn_open.grid(row=0, column=1, sticky="e")

    # ================= 模式 2：指定網址文字擷取 (濃縮) =================
    def setup_mode2_ui(self):
        self.frame_mode2.grid_columnconfigure(0, weight=1)
        self.frame_mode2.grid_rowconfigure(2, weight=1)

        top_bar = ctk.CTkFrame(self.frame_mode2, fg_color=COLOR_CARD_BG, corner_radius=12)
        top_bar.grid(row=0, column=0, padx=0, pady=(0, 15), sticky="ew")
        top_bar.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(top_bar, text="🌐 模式 2：網址文字擷取與重點整理", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_BRIGHT)
        title.grid(row=0, column=0, padx=15, pady=(12, 5), sticky="w")

        input_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        input_frame.grid(row=1, column=0, padx=15, pady=(5, 12), sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(input_frame, placeholder_text="請輸入網址 (https://...)", fg_color=COLOR_MAIN_BG, text_color=COLOR_TEXT_BRIGHT, border_color=COLOR_BORDER, height=38)
        self.url_entry.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.filter_entry = ctk.CTkEntry(input_frame, placeholder_text="篩選特定文字 (選填)", fg_color=COLOR_MAIN_BG, text_color=COLOR_TEXT_BRIGHT, border_color=COLOR_BORDER, height=38, width=160)
        self.filter_entry.grid(row=0, column=1, padx=(0, 10))

        btn_fetch = ctk.CTkButton(input_frame, text="擷取內文", command=self.run_mode2_thread, fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER, height=38, font=ctk.CTkFont(weight="bold"))
        btn_fetch.grid(row=0, column=2)

        self.scroll_mode2 = ctk.CTkScrollableFrame(self.frame_mode2, fg_color="transparent")
        self.scroll_mode2.grid(row=2, column=0, sticky="nsew")
        self.scroll_mode2.grid_columnconfigure(0, weight=1)

    def run_mode2_thread(self):
        threading.Thread(target=self.logic_mode2, daemon=True).start()

    def logic_mode2(self):
        target_url = self.url_entry.get().strip()
        filter_text = self.filter_entry.get().strip().lower()

        if not target_url.startswith("http"):
            messagebox.showwarning("提示", "請輸入完整的 URL (包含 http:// 或 https://)")
            return

        for child in self.scroll_mode2.winfo_children():
            child.destroy()

        loading_lbl = ctk.CTkLabel(self.scroll_mode2, text="✨ 正在解析網頁重點內容...", font=ctk.CTkFont(size=15), text_color=COLOR_TEXT_MUTED)
        loading_lbl.pack(pady=20)

        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            res = requests.get(target_url, headers=headers, timeout=10)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')

            paragraphs = [p.get_text().strip() for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'li']) if len(p.get_text().strip()) > 10]
            
            if filter_text:
                paragraphs = [p for p in paragraphs if filter_text in p.lower()]

            loading_lbl.destroy()

            if not paragraphs:
                ctk.CTkLabel(self.scroll_mode2, text="⚠️ 未找到符合條件的段落文字。", text_color="#FF6B6B").pack(pady=20)
                return

            for idx, text in enumerate(paragraphs, 1):
                card = ctk.CTkFrame(self.scroll_mode2, fg_color=COLOR_CARD_BG, border_color=COLOR_BORDER, border_width=1, corner_radius=10)
                card.pack(fill="x", pady=5, padx=5)

                ctk.CTkLabel(card, text=f"【重點 {idx}】", font=ctk.CTkFont(size=12, weight="bold"), text_color="#C084FC").pack(anchor="w", padx=12, pady=(8, 2))
                ctk.CTkLabel(card, text=text, font=ctk.CTkFont(size=13), text_color=COLOR_TEXT_BRIGHT, justify="left", anchor="w", wraplength=750).pack(anchor="w", padx=12, pady=(0, 10))

        except Exception as e:
            loading_lbl.destroy()
            ctk.CTkLabel(self.scroll_mode2, text=f"無法存取該網頁: {e}", text_color="#FF6B6B").pack(pady=20)

    # ================= 模式 3：截圖文字辨識 (OCR) =================
    def setup_mode3_ui(self):
        self.frame_mode3.grid_columnconfigure(0, weight=1)
        self.frame_mode3.grid_rowconfigure(2, weight=1)

        top_bar = ctk.CTkFrame(self.frame_mode3, fg_color=COLOR_CARD_BG, corner_radius=12)
        top_bar.grid(row=0, column=0, padx=0, pady=(0, 15), sticky="ew")
        top_bar.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(top_bar, text="🖼️ 模式 3：圖片/截圖文字辨識", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_BRIGHT)
        title.grid(row=0, column=0, padx=15, pady=(12, 5), sticky="w")

        input_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        input_frame.grid(row=1, column=0, padx=15, pady=(5, 12), sticky="ew")

        btn_select = ctk.CTkButton(input_frame, text="選擇截圖檔案", command=self.select_image, fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER, height=38)
        btn_select.grid(row=0, column=0, padx=(0, 10))

        self.lbl_img_path = ctk.CTkLabel(input_frame, text="尚未選取圖片", text_color=COLOR_TEXT_MUTED)
        self.lbl_img_path.grid(row=0, column=1, padx=(0, 10))

        self.ocr_target_entry = ctk.CTkEntry(input_frame, placeholder_text="搜尋目標文字 (選填)", fg_color=COLOR_MAIN_BG, text_color=COLOR_TEXT_BRIGHT, border_color=COLOR_BORDER, height=38, width=180)
        self.ocr_target_entry.grid(row=0, column=2, padx=(0, 10))

        btn_ocr = ctk.CTkButton(input_frame, text="開始辨識", command=self.run_mode3_thread, fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER, height=38, font=ctk.CTkFont(weight="bold"))
        btn_ocr.grid(row=0, column=3)

        # 輸出展現區
        out_frame = ctk.CTkFrame(self.frame_mode3, fg_color=COLOR_CARD_BG, corner_radius=12)
        out_frame.grid(row=2, column=0, sticky="nsew")
        out_frame.grid_columnconfigure(0, weight=1)
        out_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(out_frame, text="📝 提取文字結果：", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT_BRIGHT).grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")

        self.txt_mode3_out = ctk.CTkTextbox(out_frame, fg_color=COLOR_MAIN_BG, text_color=COLOR_TEXT_BRIGHT, font=ctk.CTkFont(size=13))
        self.txt_mode3_out.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")

    def select_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("圖片檔案", "*.png;*.jpg;*.jpeg;*.bmp")])
        if file_path:
            self.selected_image_path = file_path
            self.lbl_img_path.configure(text=os.path.basename(file_path), text_color=COLOR_TEXT_BRIGHT)

    def run_mode3_thread(self):
        threading.Thread(target=self.logic_mode3, daemon=True).start()

    def logic_mode3(self):
        if not self.selected_image_path:
            messagebox.showwarning("提示", "請先選擇圖片！")
            return

        self.txt_mode3_out.delete("1.0", "end")
        self.txt_mode3_out.insert("end", "✨ 載入 OCR 模型並辨識圖片中，請稍候...\n\n")

        try:
            if self.ocr_reader is None:
                self.ocr_reader = easyocr.Reader(['ch_tra', 'en'])

            img = Image.open(self.selected_image_path)
            img_array = np.array(img)
            results = self.ocr_reader.readtext(img_array)

            extracted_texts = [res[1] for res in results]
            
            self.txt_mode3_out.delete("1.0", "end")
            self.txt_mode3_out.insert("end", "=== 提取到的完整文字 ===\n\n")
            self.txt_mode3_out.insert("end", "\n".join(extracted_texts) + "\n\n")

            search_target = self.ocr_target_entry.get().strip().lower()
            if search_target:
                matched = [t for t in extracted_texts if search_target in t.lower()]
                self.txt_mode3_out.insert("end", f"=== 特殊關鍵字比對「{search_target}」===\n")
                if matched:
                    for m in matched:
                        self.txt_mode3_out.insert("end", f"🎯 找到匹配項目: {m}\n")
                else:
                    self.txt_mode3_out.insert("end", "❌ 未在圖片中找到該關鍵字。\n")

        except Exception as e:
            self.txt_mode3_out.insert("end", f"辨識失敗: {e}")

if __name__ == "__main__":
    app = DreamyPurpleApp()
    app.mainloop()