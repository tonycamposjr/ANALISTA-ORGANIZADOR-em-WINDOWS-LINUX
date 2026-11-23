@echo off
rem ==============================================================================
rem  Analista & Organizador de Arquivos - Build Windows (PyInstaller)
rem  Uso: duplo clique ou executar no cmd: build_windows.bat
rem ==============================================================================
cd /d "%~dp0"

echo Verificando dependencias de compilacao...
python -m pip install --quiet pyinstaller || goto :erro

echo Compilando executavel de Interface Grafica (AnalistaOrganizador.exe)...
python -m PyInstaller --clean AnalistaOrganizador.spec --distpath dist_windows --workpath build_win || goto :erro

echo Compilando executavel de Linha de Comando (AnalistaOrganizadorCLI.exe)...
python -m PyInstaller AnalistaOrganizadorCLI.spec --distpath dist_windows --workpath build_win || goto :erro

echo.
echo ==============================================================================
echo  Concluido com sucesso! Executaveis gerados em:
echo     dist_windows\AnalistaOrganizador.exe      (Interface Grafica)
echo     dist_windows\AnalistaOrganizadorCLI.exe   (Linha de Comando)
echo  Exemplos de uso:
echo     dist_windows\AnalistaOrganizador.exe
echo     dist_windows\AnalistaOrganizadorCLI.exe analisar D:\ -o relatorio.pdf
echo     dist_windows\AnalistaOrganizadorCLI.exe organizar D:\ --dry-run
echo ==============================================================================
pause
exit /b 0

:erro
echo ERRO no build. Certifique-se de que o Python e o pip estao instalados e no PATH.
pause
exit /b 1
