@echo off
cd /d "%~dp0"
echo ====================================
echo  LIMPEZA TOTAL DO COFRE DIGITAL
echo ====================================
echo.
echo ATENCAO: Isso apagara TODAS as senhas salvas,
echo a chave de recuperacao e os backups.
echo.
echo /p "Deseja continuar? (S/N): " opcao
if /i "%opcao%"=="S" (
    echo.
    echo Apagando banco de dados e arquivos relacionados...
    del /f /q "cofre.db" 2>nul
    del /f /q "recovery.key" 2>nul
    del /f /q "recovery_view.key" 2>nul
    del /f /q "backup_senhas.txt" 2>nul
    echo.
    echo Limpeza concluida com sucesso!
    echo.
    echo Na proxima execucao do CoffreDigital.exe,
    echo voce criara uma nova senha mestre e recebera
    echo uma nova Chave de Recuperacao.
) else (
    echo.
    echo Operacao cancelada.
)
pause