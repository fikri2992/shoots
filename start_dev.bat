@echo off
setlocal

set "ROOT=%~dp0"

where uv >nul 2>&1
if errorlevel 1 (
  echo [error] uv is not installed or not on PATH.
  exit /b 1
)

where npm.cmd >nul 2>&1
if errorlevel 1 (
  echo [error] npm is not installed or not on PATH.
  exit /b 1
)

if not exist "%ROOT%backend\.env" (
  echo [warning] backend\.env is missing. Copy backend\.env.example and configure it.
)

if not exist "%ROOT%backend\.venv\Scripts\python.exe" (
  echo Installing backend dependencies...
  pushd "%ROOT%backend"
  uv sync
  if errorlevel 1 (
    popd
    exit /b 1
  )
  popd
)

if not exist "%ROOT%frontend\node_modules" (
  echo Installing frontend dependencies...
  pushd "%ROOT%frontend"
  npm.cmd install
  if errorlevel 1 (
    popd
    exit /b 1
  )
  popd
)

echo Starting Shoots development servers...
start "Shoots Backend" /D "%ROOT%backend" cmd.exe /k "uv run uvicorn app.api.main:app --reload --port 8000"
start "Shoots Frontend" /D "%ROOT%frontend" cmd.exe /k "npm.cmd run dev"

echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo Close the two server windows, or press Ctrl+C in each, to stop development.

endlocal
