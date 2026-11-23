@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo No encuentro la instalacion. Hace doble clic en instalar.bat primero.
  pause
  exit /b 1
)
netstat -ano | findstr /R /C:":8501 .*LISTENING" /C:":8501 .*ESCUCHANDO" >nul
if not errorlevel 1 (
  echo La herramienta ya esta abierta en otra ventana negra. Te abro el navegador.
  echo Si recien actualizaste, cerra esa otra ventana negra y volve a abrir iniciar.bat.
  start "" http://localhost:8501
  pause
  exit /b 0
)
if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit"
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
  echo [general]> "%USERPROFILE%\.streamlit\credentials.toml"
  echo email = "">> "%USERPROFILE%\.streamlit\credentials.toml"
)
echo Abriendo el analizador en tu navegador: http://localhost:8501
echo No cierres esta ventana mientras uses la herramienta.
".venv\Scripts\python.exe" -m streamlit run app.py --server.port 8501
echo.
echo La herramienta se cerro. Si arriba hay un error, mandale una captura a Claude.
pause
