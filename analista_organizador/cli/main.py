"""Despachante e interface unificada de linha de comando (CLI)."""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

from .. import __version__
from ..core import categories, organizer, scanner, undo
from ..core.categories import DEFAULT_CATEGORIES, carregar_categorias, salvar_categorias
from ..core.scanner import ScanProgress
from ..reports.csv_exporter import write_csv
from ..reports.disk_report import build as build_pdf_report


def cmd_analisar(args: argparse.Namespace) -> int:
    """Executa a varredura e gera relatórios em PDF e CSV."""
    path = os.path.abspath(args.path)
    if not os.path.isdir(path):
        print(f"Erro: diretório não encontrado ou inacessível: {path}", file=sys.stderr)
        return 2

    base = os.path.basename(path.rstrip("/\\")) or "volume"
    out_pdf = args.output or os.path.join(os.path.expanduser("~"), f"indice_{base}.pdf")
    out_csv = args.csv_out or (os.path.splitext(out_pdf)[0] + ".csv")

    print(f"Analisando armazenamento em: {path}")
    progress = ScanProgress(root=path)

    def cb(files: int, size: int, frac: float, eta: str):
        if not args.quiet:
            sys.stdout.write("\r  {:3.0f}%  {:,} arquivos · {} · {}   ".format(
                frac * 100, files, scanner.human(size), eta
            ))
            sys.stdout.flush()

    progress.callback = cb
    result = scanner.scan(
        path,
        progress=progress,
        big_threshold=args.min_mb * 1024 * 1024,
        dup_mode=args.dup_mode
    )

    if not args.quiet:
        print()

    print(f"Varredura concluída: {result.total_files:,} arquivos · {scanner.human(result.total_size)} · {result.total_dirs:,} pastas")
    if result.dup_totals[1]:
        print(f"Duplicados ({args.dup_mode}): {result.dup_totals[1]} grupos desperdiçando {scanner.human(result.dup_totals[0])}")

    print(f"Gerando relatório PDF: {out_pdf}")
    build_pdf_report(result, out_pdf)
    print(f"PDF salvo com sucesso: {out_pdf}")

    if not args.no_csv:
        print(f"Exportando inventário CSV: {out_csv}")
        n = write_csv(result, out_csv)
        print(f"CSV salvo ({n:,} arquivos): {out_csv}")

    return 0


def cmd_organizar(args: argparse.Namespace) -> int:
    """Organiza os arquivos de uma pasta em categorias."""
    path = os.path.abspath(args.pasta)
    if not os.path.isdir(path):
        print(f"Erro: pasta inválida ou não encontrada: {path}", file=sys.stderr)
        return 2

    cats = carregar_categorias(args.config) if args.config else DEFAULT_CATEGORIES

    if not args.sim and not args.dry_run:
        msg = f"Organizar o conteúdo de:\n  {path}\nConfirmar operação? (s/n): "
        resp = input(msg)
        if resp.strip().lower() not in ("s", "sim", "y", "yes"):
            print("Operação cancelada pelo usuário.")
            return 0

    res = organizer.organizar_pasta(
        caminho_pasta=path,
        categorias=cats,
        dry_run=args.dry_run,
        por_data=args.por_data,
        detectar_duplicados=args.duplicados,
        on_log=print
    )

    return 0 if not res.erros else 1


def cmd_desfazer(args: argparse.Namespace) -> int:
    """Reverte uma organização previamente efetuada."""
    path = Path(args.pasta).resolve()
    caminho_log = Path(args.log).resolve() if args.log else undo.encontrar_log_mais_recente(path)

    if not caminho_log or not caminho_log.is_file():
        print(f"Nenhum arquivo de log de organização encontrado em: {path}", file=sys.stderr)
        return 2

    print(f"Utilizando log de reversão: {caminho_log.name}")
    if not args.sim:
        resp = input("Isso reverterá os movimentos registrados nesse log. Confirma? (s/n): ")
        if resp.strip().lower() not in ("s", "sim", "y", "yes"):
            print("Operação cancelada pelo usuário.")
            return 0

    res = undo.desfazer(caminho_log, on_log=print)
    return 0 if not res.erros else 1


def cmd_categorias(args: argparse.Namespace) -> int:
    """Gerencia ou exporta definições de categorias."""
    if args.exportar:
        salvar_categorias(args.exportar, DEFAULT_CATEGORIES)
        print(f"Modelo padrão de categorias exportado para: {args.exportar}")
        return 0

    print("Categorias e extensões configuradas:")
    for cat, exts in DEFAULT_CATEGORIES.items():
        print(f"  [{cat}] ({len(exts)} extensões): {', '.join(sorted(exts))}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    # Compatibilidade retroativa com o formato antigo: run.py --cli [args...]
    if argv and argv[0] == "--cli":
        argv = ["analisar"] + argv[1:]

    parser = argparse.ArgumentParser(
        prog="analista-organizador",
        description="Analista & Organizador de Arquivos — Sistema Unificado de Diagnóstico e Gestão de Disco."
    )
    parser.add_argument("--version", action="version", version=f"analista-organizador {__version__}")

    subparsers = parser.add_subparsers(dest="subcomando", help="Subcomandos disponíveis")

    # Subcomando: gui
    subparsers.add_parser("gui", help="Abre a interface gráfica (comportamento padrão quando sem argumentos)")

    # Subcomando: analisar
    p_analisar = subparsers.add_parser("analisar", help="Analisa um diretório e gera relatórios PDF/CSV")
    p_analisar.add_argument("path", help="Pasta ou unidade a analisar")
    p_analisar.add_argument("-o", "--output", default=None, help="Caminho do PDF de saída (padrão: ~/indice_<pasta>.pdf)")
    p_analisar.add_argument("--min-mb", type=int, default=50, help="Listar arquivos maiores que N MB (padrão: 50)")
    p_analisar.add_argument(
        "--dup-mode", choices=("off", "rapido", "parcial", "completo"), default="rapido",
        help="Critério de detecção de duplicados (padrão: rapido = nome + tamanho)"
    )
    p_analisar.add_argument("--no-csv", action="store_true", help="Não gerar arquivo de inventário CSV")
    p_analisar.add_argument("--csv-out", default=None, help="Caminho do CSV de saída (padrão: junto do PDF)")
    p_analisar.add_argument("--quiet", action="store_true", help="Não exibir barra de progresso no terminal")

    # Subcomando: organizar
    p_organizar = subparsers.add_parser("organizar", help="Organiza arquivos e pastas em categorias temáticas")
    p_organizar.add_argument("pasta", help="Pasta a ser organizada")
    p_organizar.add_argument("--dry-run", action="store_true", help="Simula as ações sem alterar o disco")
    p_organizar.add_argument("--por-data", action="store_true", help="Cria subpastas Ano/Mês nas categorias")
    p_organizar.add_argument("--duplicados", action="store_true", help="Isola duplicados por hash em 'Duplicados/'")
    p_organizar.add_argument("--config", help="Caminho para arquivo JSON com categorias personalizadas")
    p_organizar.add_argument("--sim", action="store_true", help="Pula confirmação interativa no terminal")

    # Subcomando: desfazer
    p_desfazer = subparsers.add_parser("desfazer", help="Reverte uma organização previamente realizada")
    p_desfazer.add_argument("pasta", nargs="?", default=".", help="Pasta contendo o arquivo de log")
    p_desfazer.add_argument("--log", help="Caminho específico do arquivo de log JSON")
    p_desfazer.add_argument("--sim", action="store_true", help="Pula confirmação interativa")

    # Subcomando: categorias
    p_cat = subparsers.add_parser("categorias", help="Consulta ou exporta modelos de categorias")
    p_cat.add_argument("--exportar", help="Exporta modelo padrão para o arquivo JSON especificado")
    p_cat.add_argument("--listar", action="store_true", help="Lista as categorias no terminal")

    # Se nenhum argumento for passado, abre a GUI
    if not argv:
        from ..ui.app import main as gui_main
        gui_main()
        return 0

    # Se o primeiro argumento for um caminho existente e não for um subcomando conhecido
    primeiro = argv[0]
    if primeiro not in ("gui", "analisar", "organizar", "desfazer", "categorias", "-h", "--help", "--version"):
        if os.path.exists(primeiro):
            # Se foi passado um caminho diretamente, assumir 'analisar' por convenção
            argv = ["analisar"] + argv

    args = parser.parse_args(argv)

    if args.subcomando == "gui" or not args.subcomando:
        from ..ui.app import main as gui_main
        gui_main()
        return 0
    elif args.subcomando == "analisar":
        return cmd_analisar(args)
    elif args.subcomando == "organizar":
        return cmd_organizar(args)
    elif args.subcomando == "desfazer":
        return cmd_desfazer(args)
    elif args.subcomando == "categorias":
        return cmd_categorias(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
