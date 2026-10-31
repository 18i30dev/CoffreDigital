@echo off
echo ====================================
echo  Instalador do Coffre Digital
echo ====================================
echo.
echo Instalando dependencias do Python...
echo.
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
echo ====================================
echo  Instalacao concluida!
echo ====================================
echo.
pause