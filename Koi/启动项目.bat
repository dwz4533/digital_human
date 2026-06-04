@echo off
echo 启动金鱼交互程序...
echo 请确保Unity程序已启动并显示"服务器已启动"提示
echo.
start "" "Koi_fishV1.exe"
timeout /t 3 /nobreak >nul
echo 正在发送测试指令...
python SendCommends.py
pause