@echo off
chcp 65001 >nul
title 打包工具 - PyInstaller

echo =========================================
echo 📦 正在將專案打包為 Windows 執行檔...
echo =========================================

pyinstaller --noconsole --onedir --name="AI_Assistant" --add-data "appp.py;." --collect-all streamlit gui_launcher.py

echo.
echo =========================================
echo 🎉 打包程序結束，請確認上方是否有紅色或 Error 訊息。
echo =========================================
pause