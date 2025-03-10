@echo off
echo ===== CAI DAT VA CHAY BOT GIAO DICH =====
echo.

REM Kiem tra quyen admin
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
    echo Ban can chay voi quyen Administrator
    echo Click chuot phai va chon "Run as administrator"
    pause
    exit /b
)

echo Kiem tra Python...
where python >nul 2>&1
if %errorlevel% NEQ 0 (
    echo Python chua duoc cai dat
    echo Vui long cai dat Python tu https://www.python.org/downloads/
    echo Dam bao tick chon "Add Python to PATH" khi cai dat
    pause
    exit /b
)

echo Kiem tra phien ban Python...
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Phien ban Python: %PYTHON_VERSION%

echo.
echo Cai dat cac thu vien can thiet...
python setup_dependencies.py

echo.
echo Thiet lap cau hinh rui ro...
python risk_level_manager.py --create-default

echo.
echo Khoi dong giao dien do hoa...
echo "Neu khong hien thi giao dien, hay chay lenh: python bot_gui.py"
python bot_gui.py

pause