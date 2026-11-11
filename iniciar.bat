@echo off
rem JASSHINE - inicia la aplicación en Windows (crea el entorno la primera vez)
cd /d "%~dp0"
if "%MONGODB_URI%"=="" if not exist ".env" (
  echo ERROR: configura MONGODB_URI con la URI de MongoDB Atlas antes de iniciar.
  echo Configura MONGODB_URI en el archivo .env o como variable de entorno.
  exit /b 1
)
if not exist .venv\Scripts\python.exe (
  echo Creando entorno de Python...
  py -m venv .venv
)
.venv\Scripts\python.exe -m pip install -r requirements.txt -q
echo.
echo JASSHINE listo en http://127.0.0.1:5000   (Ctrl+C para detener)
.venv\Scripts\python.exe app.py
