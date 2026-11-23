#!/usr/bin/env python3
"""Ponto de entrada universal do Analista & Organizador de Arquivos.

Uso:
    Interface Gráfica:
        python3 run.py
        python3 run.py gui

    Linha de Comando:
        python3 run.py analisar /caminho [-o indice.pdf] [--dup-mode rapido]
        python3 run.py organizar /caminho [--dry-run] [--por-data] [--duplicados]
        python3 run.py desfazer /caminho [--log arquivo.json]
        python3 run.py categorias [--listar | --exportar config.json]
"""

import sys
from analista_organizador.cli.main import main

if __name__ == "__main__":
    sys.exit(main())
