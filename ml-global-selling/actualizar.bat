@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Descargando la ultima version del Analizador ML Global...
set "TMPDIR=%TEMP%\mlglobal_actualizacion"
if exist "%TMPDIR%" rmdir /s /q "%TMPDIR%"
mkdir "%TMPDIR%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; Invoke-WebRequest -UseBasicParsing 'https://codeload.github.com/NicoKosoy/demos/zip/refs/heads/claude/wizardly-mccarthy-02vt1p' -OutFile '%TMPDIR%\codigo.zip'; Expand-Archive '%TMPDIR%\codigo.zip' '%TMPDIR%\codigo' -Force"
if errorlevel 1 (
  echo No se pudo descargar. Revisa tu conexion a internet y volve a intentar.
  pause
  exit /b 1
)
set "SRC="
for /d %%D in ("%TMPDIR%\codigo\*") do set "SRC=%%D\ml-global-selling"
if not exist "%SRC%\app.py" (
  echo La descarga no tiene la herramienta. Avisale a Claude.
  pause
  exit /b 1
)
robocopy "%SRC%" "%CD%" /E /XD datos .venv /XF actualizar.bat /R:1 /W:1 /NFL /NDL /NJH /NJS /NP >nul
if %errorlevel% GEQ 8 (
  echo No se pudieron copiar los archivos. Cerra la herramienta y volve a intentar.
  pause
  exit /b 1
)
rmdir /s /q "%TMPDIR%"
if exist .venv\Scripts\activate.bat (
  call .venv\Scripts\activate.bat
  python -m pip install -q -r requirements.txt
)
echo.
echo Listo, ya tenes la ultima version. Tus datos no se tocaron.
echo Abri la herramienta con iniciar.bat
pause
