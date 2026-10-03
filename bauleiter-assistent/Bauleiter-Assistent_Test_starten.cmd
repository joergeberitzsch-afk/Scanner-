@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Bauleiter-Assistent Testversion

rem --- Python suchen: Python-Launcher, dann PATH, dann die ueblichen Installationsordner
set "PY="
py -3 -c "import sys" >nul 2>&1 && set "PY=py -3"
if not defined PY python -c "import sys" >nul 2>&1 && set "PY=python"
if not defined PY for %%V in (313 312 311 310 39 38) do (
    if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
)
if not defined PY (
    echo.
    echo  Python wurde nicht gefunden.
    echo  Bitte Python 3.8 oder neuer von https://www.python.org/downloads/ installieren
    echo  und bei der Installation "Add python.exe to PATH" anhaken.
    echo.
    pause
    exit /b 1
)

rem --- Abhaengigkeiten beim ersten Start installieren (nur falls requirements.txt vorhanden)
if exist requirements.txt if not exist ".abhaengigkeiten_ok" (
    echo Installiere benoetigte Pakete ...
    %PY% -m pip install --disable-pip-version-check -r requirements.txt
    if errorlevel 1 (
        echo.
        echo  Die Pakete konnten nicht installiert werden. Internetverbindung pruefen.
        pause
        exit /b 1
    )
    echo ok> ".abhaengigkeiten_ok"
)

rem --- Voraussetzungen pruefen: 0 = startbereit, 2 = laeuft bereits, sonst Fehler
%PY% server.py --pruefen
set "ERGEBNIS=%ERRORLEVEL%"
if "%ERGEBNIS%"=="2" (
    %PY% server.py
    exit /b 0
)
if not "%ERGEBNIS%"=="0" (
    echo.
    pause
    exit /b 1
)

rem --- Server minimiert starten; der Server oeffnet den Browser selbst, sobald er bereit ist
start "Bauleiter-Assistent Testversion" /min %PY% server.py
exit /b 0
