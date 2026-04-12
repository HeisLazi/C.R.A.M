@echo off
:: ════════════════════════════════════════════════════════════════════════
::  C.R.A.M — The Unbound  ·  Windows .exe Build Script
::  Run from the project root:   build_windows.bat
::  Output folder:               dist\CRAM_The_Unbound\
:: ════════════════════════════════════════════════════════════════════════

echo.
echo ========================================
echo  C.R.A.M -- The Unbound  Build Script
echo ========================================
echo.

:: Use "python -m" so it works with Microsoft Store Python (scripts not on PATH)
:: ── Use venv if it exists, otherwise fall back to system Python ──────────────
if exist "venv\Scripts\python.exe" (
    set PYTHON=venv\Scripts\python.exe
    echo     Using venv Python.
) else (
    set PYTHON=python
    echo     No venv found -- using system Python. Run 'python -m venv venv' for cleaner builds.
)

echo [1/3] Installing launcher dependencies...
%PYTHON% -m pip install -r requirements_launcher.txt --quiet
if errorlevel 1 (
    echo ERROR: pip install failed. Make sure Python is installed and on PATH.
    pause & exit /b 1
)

:: ── Detect site-packages from the chosen Python ──────────────────────────────
echo     Detecting site-packages location...
for /f "tokens=*" %%i in ('%PYTHON% -c "import site; print(site.getsitepackages()[0])"') do set SITE_PACKAGES=%%i
echo     Found: %SITE_PACKAGES%

:: ── Clean old build folder to avoid PermissionError ──────────────────────────
:: (Happens if the .exe was running during a previous build)
echo     Cleaning old dist folder...
if exist "dist\CRAM_The_Unbound" (
    taskkill /F /IM "CRAM_The_Unbound.exe" 2>nul
    timeout /t 1 /nobreak >nul
    rmdir /S /Q "dist\CRAM_The_Unbound" 2>nul
)

echo [2/3] Building .exe with PyInstaller...
echo.

%PYTHON% -m PyInstaller ^
  --noconfirm ^
  --onedir ^
  --windowed ^
  --name "CRAM_The_Unbound" ^
  --paths "%SITE_PACKAGES%" ^
  --add-data "static;static" ^
  --add-data "play.html;." ^
  --add-data "CRAM_SUBJECT_TEMPLATE.json;." ^
  --collect-all "uvicorn" ^
  --collect-all "webview" ^
  --hidden-import="fastapi" ^
  --hidden-import="fastapi.middleware" ^
  --hidden-import="fastapi.middleware.cors" ^
  --hidden-import="fastapi.staticfiles" ^
  --hidden-import="fastapi.responses" ^
  --hidden-import="starlette" ^
  --hidden-import="starlette.middleware" ^
  --hidden-import="starlette.middleware.cors" ^
  --hidden-import="starlette.staticfiles" ^
  --hidden-import="starlette.responses" ^
  --hidden-import="starlette.routing" ^
  --hidden-import="pydantic" ^
  --hidden-import="pydantic.main" ^
  --hidden-import="pydantic_core" ^
  --hidden-import="anyio" ^
  --hidden-import="anyio._backends._asyncio" ^
  --hidden-import="uvicorn.logging" ^
  --hidden-import="uvicorn.loops" ^
  --hidden-import="uvicorn.loops.auto" ^
  --hidden-import="uvicorn.protocols.http" ^
  --hidden-import="uvicorn.protocols.http.auto" ^
  --hidden-import="uvicorn.protocols.websockets" ^
  --hidden-import="uvicorn.protocols.websockets.auto" ^
  --hidden-import="uvicorn.lifespan" ^
  --hidden-import="uvicorn.lifespan.on" ^
  --hidden-import="backend.main" ^
  --hidden-import="backend.combat" ^
  --hidden-import="backend.question_engine" ^
  --hidden-import="backend.overworld" ^
  --hidden-import="backend.codex" ^
  --hidden-import="backend.world" ^
  --hidden-import="backend.node_interaction" ^
  launcher.py

if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed. See output above.
    pause & exit /b 1
)

:: ── Copy subjects folder into the build output ───────────────────────────────
echo.
echo [3/3] Copying subjects into build...
robocopy "subjects" "dist\CRAM_The_Unbound\subjects" /E /NFL /NDL /NJH /NJS /NC /NS 1>nul
if %errorlevel% GEQ 8 (
    echo     WARNING: robocopy failed, creating empty subjects folder instead.
    mkdir "dist\CRAM_The_Unbound\subjects" 2>nul
) else (
    echo     subjects\ copied OK.
)

:: ── Done ─────────────────────────────────────────────────────────────────────
echo.
echo ========================================
echo  BUILD COMPLETE
echo ========================================
echo.
echo  Game folder:  dist\CRAM_The_Unbound\
echo  Launch with:  dist\CRAM_The_Unbound\CRAM_The_Unbound.exe
echo.
echo  To share with playtesters:
echo    Zip the entire  dist\CRAM_The_Unbound\  folder.
echo    Players unzip anywhere and run CRAM_The_Unbound.exe.
echo    They drop new subject folders into the subjects\ folder next to the .exe.
echo.
pause
