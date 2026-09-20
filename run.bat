@echo off
chcp 65001 >nul
title AI 輔助系統 - 啟動中...

echo =========================================
echo 🚀 正在啟動 伺服器端 (appp.py) 與 連接端...
echo =========================================

:: 啟動 gui_launcher.py (其內部會自動呼叫 appp.py 並清理行程)
python gui_launcher.py

pause