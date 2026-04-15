@echo off
title Factory System Startup
cd /d "%~dp0"

echo ============================================================
echo  CEG5003 Factory System - One-Click Startup
echo ============================================================
echo.

echo [1/7] Starting Mosquitto (MQTT broker)...
net start mosquitto >nul 2>&1
if %errorlevel%==0 (
    echo       OK - Mosquitto started
) else (
    echo       Already running or failed - continuing
)

echo [2/7] Starting InfluxDB...
tasklist /fi "imagename eq influxd.exe" 2>nul | find /i "influxd.exe" >nul
if %errorlevel%==0 (
    echo       Already running
) else (
    start "InfluxDB" /min cmd /k "C:\Users\97350\AppData\Local\Microsoft\WinGet\Packages\InfluxData.InfluxDB.OSS_Microsoft.Winget.Source_8wekyb3d8bbwe\influxd.exe"
    echo       OK - InfluxDB started
)

echo [3/7] Starting Docker Desktop...
tasklist /fi "imagename eq Docker Desktop.exe" 2>nul | find /i "Docker Desktop.exe" >nul
if %errorlevel%==0 (
    echo       Already running
) else (
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo       Waiting for Docker to start...
    timeout /t 15 /nobreak >nul
)

echo [4/7] Starting Grafana (Docker container)...
docker start grafana >nul 2>&1
if %errorlevel%==0 (
    echo       OK - Grafana container started
) else (
    echo       Failed - check Docker is running
)

echo.
echo Waiting for services to initialize...
timeout /t 3 /nobreak >nul

echo [5/7] Starting MQTT Bridge...
start "MQTT Bridge" cmd /k "cd /d %~dp0 && python mqtt_bridge/main.py"

echo [6/7] Starting Logistics Controller...
start "Logistics Ctrl" cmd /k "cd /d %~dp0 && python logistics_ctrl/branch_controller.py"

echo [7/7] Starting Factory Agent...
start "Factory Agent" cmd /k "cd /d %~dp0\factory_agent && python -m uvicorn web_app:app --host 127.0.0.1 --port 8891"

echo.
echo Waiting for agent to initialize...
timeout /t 4 /nobreak >nul

echo Opening browser...
start http://127.0.0.1:8891
start http://localhost:3000

echo.
echo ============================================================
echo  All done! Remember to open JaamSim manually:
echo  simulation_files\simulation.cfg
echo ============================================================
pause
