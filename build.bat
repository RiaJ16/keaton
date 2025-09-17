@echo off
REM ==================================================
REM Compilación de Keaton con Nuitka
REM ==================================================

REM Activar entorno virtual (ajusta "venv11" si tu venv tiene otro nombre)
call venv11\Scripts\activate

REM Borrar compilaciones anteriores
if exist build (
    echo [INFO] Limpiando carpeta build...
    rmdir /s /q build
)

echo [INFO] Compilando Keaton.exe con Nuitka...

python -m nuitka main.py ^
    --standalone ^
    --enable-plugin=pyside6 ^
    --include-data-dir=themes=themes ^
    --include-data-dir=threads=threads ^
    --include-data-dir=icons=icons ^
    --include-data-dir=styles=styles ^
     --windows-console-mode=disable ^
    --windows-icon-from-ico=keaton.ico ^
    --output-filename=Keaton.exe ^
    --output-dir=build

if %errorlevel% neq 0 (
    echo [ERROR] Hubo un problema en la compilación.
    pause
    exit /b %errorlevel%
)

echo [OK] Compilación completada.
echo El ejecutable está en build\Keaton.exe

pause
