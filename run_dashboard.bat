@echo off
chcp 65001 >nul
echo ===================================================
echo   FM_REA_HeadCoach 실시간 전술 분석 서버 실행기
echo ===================================================
cd /d "%~dp0backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause

