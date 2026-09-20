import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import requests
from bs4 import BeautifulSoup
from PIL import Image
import easyocr
import numpy as np
import os

# 設定視覺主題
ctk.set_appearance_mode("System")  # 支援 System, Dark, Light
ctk.set_default_color_theme("blue")  # 主題顏色: blue, green, dark-blue

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("多功能資訊擷取桌面機器人 v1.0")
        self.geometry("980x680")
        self.minsize(800, 500)

        # 變數存放
        self.ocr_reader = None
        self.selected_image_path = None

        # 佈局配置 (側邊欄 + 主內容區)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ================= 建立側邊欄 =================
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="🤖 爬蟲助理", font=ctk.CTkFont(size=22, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 20))

        self.btn_mode1 = ctk.CTkButton(self.sidebar_frame, text="🔍 關鍵字搜尋", command=self.show_mode1)
        self.btn_mode1.grid(row=1, column=0, padx=20, pady=10)

        self.btn_mode2 = ctk.CTkButton(self.sidebar_frame, text="🌐 網址文字擷取", command=self.show_mode2)
        self.btn_mode2.grid(row=2, column=0, padx=20, pady=10)

        self.btn_mode3 = ctk.CTkButton(self.sidebar_frame, text="🖼️ 截圖辨識 (OCR)", command=self.show_mode3)
        self.btn_mode3.grid(row=3, column=0, padx=20, pady=10)

        # 主題切換按鈕
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(
            self.sidebar_frame, values=["System", "Dark", "Light"], command=self.change_appearance_mode
        )
        self.appearance_mode_optionemenu.grid(row=5, column=0, padx=20, pady=(10, 20))

        # ================= 建立各模式面板 =================
        self.frame_mode1 = ctk.CTkFrame(self, corner_radius=10)
        self.frame_mode2 = ctk.CTkFrame(self, corner_radius=10)
        self.frame_mode3 = ctk.CTkFrame(self, corner_radius=10)

        self.setup_mode1_ui()
        self.setup_mode2_ui()
        self.setup_mode3_ui()

        # 預設顯示模式 1
        self.show_mode1()

    # ---------------- 介面切換邏輯 ----------------
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

    def change_appearance_mode(self, new_mode):
        ctk.set_appearance_mode(new_mode)

    # ---------------- 模式 1 UI 與邏輯 ----------------
    def setup_mode1_ui(self):
        self.frame_mode1.grid_columnconfigure(0, weight=1)
        self.frame_mode1.grid_rowconfigure(3, weight=1)

        title = ctk.CTkLabel(self.frame_mode1, text="🔍 模式 1：關鍵字搜尋", font=ctk.CTkFont(size=18, weight="bold"))
        title.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="w")

        self.kw_entry = ctk.CTkEntry(self.frame_mode1, placeholder_text="請輸入搜尋關鍵字 (例如：人工智能)")
        self.kw_entry.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.btn_kw_search = ctk.CTkButton(self.frame_mode1, text="開始搜尋", command=self.run_mode1_thread)
        self.btn_kw_search.grid(row=2, column=0, padx=20, pady=5, sticky="w")

        self.txt_mode1_out = ctk.CTkTextbox(self.frame_mode1, font=ctk.CTkFont(size=13))
        self.txt_mode1_out.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="nsew")

    def run_mode1_thread(self):
        threading.Thread(target=self.logic_mode1, daemon=True).start()

    def logic_mode1(self):
        kw = self.kw_entry.get().strip()
        if not kw:
            messagebox.showwarning("警告", "請輸入關鍵字！")
            return
        
        self.txt_mode1_out.delete("1.0", "end")
        self.txt_mode1_out.insert("end", f"正在搜尋「{kw}」中...\n\n")
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        url = f"https://html.duckduckgo.com/html/?q={kw}"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            titles = soup.find_all('a', class_='result__a', limit=8)
            snippets = soup.find_all('a', class_='result__snippet', limit=8)
            
            if not titles:
                self.txt_mode1_out.insert("end", "未找到結果或遭遇請求限制。")
                return

            for idx, (t, s) in enumerate(zip(titles, snippets), 1):
                res_str = f"[{idx}] {t.get_text().strip()}\n連結: {t['href']}\n摘要: {s.get_text().strip()}\n{'-'*60}\n"
                self.txt_mode1_out.insert("end", res_str)
        except Exception as e:
            self.txt_mode1_out.insert("end", f"搜尋發生錯誤: {e}")

    # ---------------- 模式 2 UI 與邏輯 ----------------
    def setup_mode2_ui(self):
        self.frame_mode2.grid_columnconfigure(0, weight=1)
        self.frame_mode2.grid_rowconfigure(4, weight=1)

        title = ctk.CTkLabel(self.frame_mode2, text="🌐 模式 2：指定網址文字擷取", font=ctk.CTkFont(size=18, weight="bold"))
        title.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="w")

        self.url_entry = ctk.CTkEntry(self.frame_mode2, placeholder_text="請輸入網址 (https://...)")
        self.url_entry.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        self.filter_entry = ctk.CTkEntry(self.frame_mode2, placeholder_text="關鍵字過濾 (選填，例如：價格/標題)")
        self.filter_entry.grid(row=2, column=0, padx=20, pady=5, sticky="ew")

        self.btn_url_fetch = ctk.CTkButton(self.frame_mode2, text="擷取網頁文字", command=self.run_mode2_thread)
        self.btn_url_fetch.grid(row=3, column=0, padx=20, pady=5, sticky="w")

        self.txt_mode2_out = ctk.CTkTextbox(self.frame_mode2, font=ctk.CTkFont(size=13))
        self.txt_mode2_out.grid(row=4, column=0, padx=20, pady=(10, 20), sticky="nsew")

    def run_mode2_thread(self):
        threading.Thread(target=self.logic_mode2, daemon=True).start()

    def logic_mode2(self):
        target_url = self.url_entry.get().strip()
        filter_text = self.filter_entry.get().strip().lower()

        if not target_url.startswith("http"):
            messagebox.showwarning("警告", "請輸入正確的 URL (需包含 http:// 或 https://)")
            return

        self.txt_mode2_out.delete("1.0", "end")
        self.txt_mode2_out.insert("end", f"正在讀取網址：{target_url}...\n\n")

        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            res = requests.get(target_url, headers=headers, timeout=10)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')

            paragraphs = [p.get_text().strip() for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'li']) if p.get_text().strip()]
            
            if filter_text:
                paragraphs = [p for p in paragraphs if filter_text in p.lower()]

            if not paragraphs:
                self.txt_mode2_out.insert("end", "未找到符合的內容。")
                return

            for idx, text in enumerate(paragraphs, 1):
                self.txt_mode2_out.insert("end", f"[{idx}] {text}\n\n")
        except Exception as e:
            self.txt_mode2_out.insert("end", f"讀取網頁失敗：{e}")

    # ---------------- 模式 3 UI 與邏輯 ----------------
    def setup_mode3_ui(self):
        self.frame_mode3.grid_columnconfigure(0, weight=1)
        self.frame_mode3.grid_rowconfigure(5, weight=1)

        title = ctk.CTkLabel(self.frame_mode3, text="🖼️ 模式 3：截圖/圖片文字辨識 (OCR)", font=ctk.CTkFont(size=18, weight="bold"))
        title.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="w")

        self.btn_select_img = ctk.CTkButton(self.frame_mode3, text="選擇圖片檔案", command=self.select_image)
        self.btn_select_img.grid(row=1, column=0, padx=20, pady=5, sticky="w")

        self.lbl_img_path = ctk.CTkLabel(self.frame_mode3, text="尚未選擇圖片", text_color="gray")
        self.lbl_img_path.grid(row=2, column=0, padx=20, pady=0, sticky="w")

        self.ocr_target_entry = ctk.CTkEntry(self.frame_mode3, placeholder_text="比對特定文字 (選填)")
        self.ocr_target_entry.grid(row=3, column=0, padx=20, pady=5, sticky="ew")

        self.btn_start_ocr = ctk.CTkButton(self.frame_mode3, text="執行 OCR 辨識", command=self.run_mode3_thread)
        self.btn_start_ocr.grid(row=4, column=0, padx=20, pady=5, sticky="w")

        self.txt_mode3_out = ctk.CTkTextbox(self.frame_mode3, font=ctk.CTkFont(size=13))
        self.txt_mode3_out.grid(row=5, column=0, padx=20, pady=(10, 20), sticky="nsew")

    def select_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("圖片檔案", "*.png;*.jpg;*.jpeg;*.bmp")])
        if file_path:
            self.selected_image_path = file_path
            self.lbl_img_path.configure(text=f"已選取：{os.path.basename(file_path)}", text_color="white")

    def run_mode3_thread(self):
        threading.Thread(target=self.logic_mode3, daemon=True).start()

    def logic_mode3(self):
        if not self.selected_image_path:
            messagebox.showwarning("警告", "請先選擇圖片！")
            return

        self.txt_mode3_out.delete("1.0", "end")
        self.txt_mode3_out.insert("end", "辨識中... (首次執行需載入 OCR 模型，請稍候)\n\n")

        try:
            if self.ocr_reader is None:
                self.ocr_reader = easyocr.Reader(['ch_tra', 'en'])

            img = Image.open(self.selected_image_path)
            img_array = np.array(img)
            results = self.ocr_reader.readtext(img_array)

            extracted_texts = [res[1] for res in results]
            
            self.txt_mode3_out.delete("1.0", "end")
            self.txt_mode3_out.insert("end", "=== 圖片完整識別結果 ===\n")
            self.txt_mode3_out.insert("end", "\n".join(extracted_texts) + "\n\n")

            search_target = self.ocr_target_entry.get().strip().lower()
            if search_target:
                matched = [t for t in extracted_texts if search_target in t.lower()]
                self.txt_mode3_out.insert("end", f"=== 比對結果「{search_target}」===\n")
                if matched:
                    for m in matched:
                        self.txt_mode3_out.insert("end", f"🎯 找到匹配：{m}\n")
                else:
                    self.txt_mode3_out.insert("end", "❌ 未找到包含該關鍵字的文字。\n")

        except Exception as e:
            self.txt_mode3_out.insert("end", f"OCR 辨識失敗：{e}")

if __name__ == "__main__":
    app = App()
    app.mainloop()