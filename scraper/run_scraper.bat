@echo off
REM ==============================================
REM Facebook Marketplace Scraper - Windows
REM ==============================================
REM Uso: Doble click en este archivo
REM ==============================================

echo =============================================
echo Facebook Marketplace Scraper
echo =============================================
echo.

cd /d "%~dp0"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no esta instalado
    echo Descargalo de: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

REM Install dependencies if needed
if not exist "venv" (
    echo Instalando dependencias...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

REM Run scraper
echo.
echo Corriendo scraper...
echo.
python -m scraper.main --db-path data\listings.db

echo.
echo Scraper completado!
echo.
pause
