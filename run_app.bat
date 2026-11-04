@echo off
title SecureShield Pro - File Manager
cd /d "%~dp0"
echo ========================================================
echo   Starting SecureShield Pro Web Application...
echo   Opening browser at http://localhost:8501
echo ========================================================
python -m streamlit run app.py
if errorlevel 1 (
    echo.
    echo Streamlit stopped or encountered an error.
    pause
)
