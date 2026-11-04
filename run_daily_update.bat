@echo off
chcp 65001 > nul
echo ========================================================
echo   正在執行台灣基金每日淨值與多天期報酬更新...
echo ========================================================
python "%~dp0update_fund_data.py"
echo.
echo 更新完成！您現在可以開啟 fund_dashboard.html 查閱最新資料。
pause
