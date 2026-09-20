import os
import sys
import time
import socket
import subprocess
import urllib.request
import webbrowser

# 嘗試載入 pywebview 提供獨立原生桌面視窗；若未安裝則自動切換為系統瀏覽器模式
try:
    import webview
    HAS_WEBVIEW = True
except ImportError:
    HAS_WEBVIEW = False

HOST = "127.0.0.1"
PORT = 8501

def get_resource_path(relative_path):
    """ 獲取資源檔案路徑 (相容 PyInstaller 打包後的臨時目錄 _MEIPASS) """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def is_port_in_use(port):
    """ 檢查通訊埠是否已被佔用 """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((HOST, port)) == 0

def wait_for_server(url, timeout=15):
    """ 持續輪詢等待 Streamlit 伺服器啟動完畢 """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.4)
    return False

def start_streamlit():
    """ 啟動 Streamlit 伺服器端子行程 """
    script_path = get_resource_path("appp.py")
    
    # Windows 系統下隱藏黑色的 CMD 視窗
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW

    # 判斷是否為 PyInstaller 打包後的環境
    if getattr(sys, 'frozen', False):
        cmd = [
            sys.executable, "-m", "streamlit", "run", script_path,
            f"--server.port={PORT}",
            "--server.headless=true",
            "--global.developmentMode=false"
        ]
    else:
        cmd = [
            "streamlit", "run", script_path,
            f"--server.port={PORT}",
            "--server.headless=true",
            "--global.developmentMode=false"
        ]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags
    )
    return process

def main():
    server_process = None
    url = f"http://{HOST}:{PORT}"

    # 1. 若伺服器未運行，開啓背景 Streamlit 子行程
    if not is_port_in_use(PORT):
        server_process = start_streamlit()
        if not wait_for_server(url):
            print("❌ Streamlit 伺服器啟動失敗或超時。")
            if server_process:
                server_process.kill()
            sys.exit(1)

    # 2. 啟動 GUI 介面
    try:
        if HAS_WEBVIEW:
            # 建立獨立的 App 桌面視窗
            webview.create_window(
                "🤖 智慧資訊擷取與 AI 輔助系統",
                url,
                width=1280,
                height=820,
                resizable=True
            )
            webview.start()
        else:
            # 未安裝 pywebview 時，降級直接使用預設瀏覽器開啟
            webbrowser.open(url)
            print("💡 提醒：安裝 `pip install pywebview` 可獲得獨立桌面視窗體驗。")
    finally:
        # 3. 視窗關閉時自動關閉背景伺服器行程，防止殘留佔用 Port
        if server_process:
            server_process.terminate()
            server_process.wait()

if __name__ == "__main__":
    main()