@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Instalando el Analizador ML Global...
where py >nul 2>nul
if %errorlevel%==0 (set "PY=py -3") else (set "PY=python")
%PY% --version >nul 2>nul
if errorlevel 1 (
  echo.
  echo No encontre Python. Instalalo desde https://www.python.org/downloads/
  echo y tilda "Add python.exe to PATH" durante la instalacion. Despues volve a abrir este archivo.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe %PY% -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Fallo la instalacion de dependencias. Revisa tu conexion y volve a intentar.
  pause
  exit /b 1
)
python cli.py init
echo.
echo Listo. Para abrir la herramienta hace doble clic en iniciar.bat
pause
