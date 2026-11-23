#!/bin/bash
# ==============================================================================
#  Analista & Organizador de Arquivos — Build Linux (PyInstaller)
#  Uso: ./build_linux.sh
# ==============================================================================
set -e
cd "$(dirname "$0")"

echo "Verificando dependências de compilação..."
python3 -m pip install --quiet --user pyinstaller 2>/dev/null \
  || python3 -m pip install --quiet --break-system-packages --user pyinstaller 2>/dev/null \
  || echo "PyInstaller já presente no ambiente."

echo "Compilando executável com Interface Gráfica (AnalistaOrganizador)..."
python3 -m PyInstaller --clean AnalistaOrganizador.spec --distpath dist_linux --workpath build_lin

echo "Compilando executável Linha de Comando (AnalistaOrganizadorCLI)..."
python3 -m PyInstaller AnalistaOrganizadorCLI.spec --distpath dist_linux --workpath build_lin

# Criar links de compatibilidade retroativa para scripts antigos
cd dist_linux
ln -sf AnalistaOrganizador DiskIndex 2>/dev/null || true
ln -sf AnalistaOrganizadorCLI DiskIndexCLI 2>/dev/null || true
cd ..

chmod +x dist_linux/AnalistaOrganizador dist_linux/AnalistaOrganizadorCLI 2>/dev/null || true

echo
echo "=============================================================================="
echo " Concluído com sucesso! Executáveis gerados em:"
echo "   dist_linux/AnalistaOrganizador      (Interface Gráfica)"
echo "   dist_linux/AnalistaOrganizadorCLI   (Linha de Comando)"
echo " Exemplos de uso:"
echo "   ./dist_linux/AnalistaOrganizador"
echo "   ./dist_linux/AnalistaOrganizadorCLI analisar /caminho -o relatorio.pdf"
echo "   ./dist_linux/AnalistaOrganizadorCLI organizar /caminho --dry-run"
echo "=============================================================================="
