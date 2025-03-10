@echo off
echo ===== CHAY BOT CHE DO 24/7 =====
echo.

REM Kiem tra quyen admin
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
    echo Ban can chay voi quyen Administrator
    echo Click chuot phai va chon "Run as administrator"
    pause
    exit /b
)

REM Chon muc rui ro
echo Chon muc do rui ro:
echo [1] 10% (Thap)
echo [2] 15% (Trung binh thap)
echo [3] 20% (Trung binh)
echo [4] 30% (Cao)
choice /c 1234 /n /m "Nhap lua chon (1-4): "

set risk_level=10
if %errorlevel% == 1 set risk_level=10
if %errorlevel% == 2 set risk_level=15
if %errorlevel% == 3 set risk_level=20
if %errorlevel% == 4 set risk_level=30

echo.
echo Da chon muc rui ro: %risk_level%%
echo.

echo Khoi dong bot voi Guardian...
echo.
echo Bot se tu dong khoi dong lai khi gap loi.
echo.
echo De dung bot, dong cua so nay hoac nhan Ctrl+C.
echo.

python auto_restart_guardian.py --risk-level %risk_level%

pause