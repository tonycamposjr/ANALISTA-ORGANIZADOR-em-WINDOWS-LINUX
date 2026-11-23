"""Montagem do relatório analítico em PDF: consolida métricas do ScanResult em documento executivo."""

import os
import shutil
import time
from datetime import date
from typing import Optional

from ..core import scanner
from ..core.categories import color_of
from .pdf_writer import PDF, PAGE_W, PAGE_H, MARGIN, USABLE_W, COLORS


def _num(n: int) -> str:
    return "{:,}".format(n).replace(",", ".")


def _today() -> str:
    return date.strftime(date.today(), "%d/%m/%Y")


def _dt(ts: float) -> str:
    return time.strftime("%d/%m/%Y", time.localtime(ts))


def build(result: scanner.ScanResult, out_path: str, footer_note: str = "") -> str:
    """Gera o relatório analítico em formato PDF a partir dos dados do ScanResult."""
    pdf = PDF()
    size_total = max(result.total_size, 1)

    def pct(n: int | float) -> str:
        return ("{:.1f}".format(n / size_total * 100).replace(".", ",") + "%")

    # ---------- Cabeçalho do Documento ----------
    pdf.text(
        MARGIN, PAGE_H - MARGIN - 6, 19,
        "Relatório Analítico de Armazenamento — {}".format(os.path.basename(result.root) or "Raiz"),
        "F2", COLORS["navy"]
    )
    pdf.y -= 24
    pdf.text(
        MARGIN, pdf.y, 9,
        "Levantamento da árvore de arquivos · Gerado em {} · Caminho: {}".format(_today(), result.root),
        "F1", COLORS["muted"]
    )
    pdf.y -= 10

    # ---------- Cartões de Resumo Global ----------
    try:
        usage = shutil.disk_usage(result.root)
        free_txt = scanner.human(usage.free)
        total_txt = scanner.human(usage.total)
    except OSError:
        free_txt, total_txt = "-", "-"

    pdf.cards([
        (scanner.human(result.total_size), "Espaço Usado"),
        (free_txt, "Livre (Total {})".format(total_txt)),
        (_num(result.total_files), "Total de Arquivos"),
        (_num(result.total_dirs), "Pastas Mapeadas"),
        (_num(len(result.by_ext)), "Tipos de Extensões"),
    ])

    # ---------- Idade dos Dados (Histórico) ----------
    if result.oldest and result.newest:
        pdf.text(MARGIN, pdf.y, 8.6, "Arquivo mais antigo:", "F2", COLORS["navy"])
        pdf.text(
            MARGIN + 92, pdf.y, 8.6,
            "{}  ({})".format(_dt(result.oldest[0]), pdf.trunc(result.oldest[1], 8.6, "F1", 160)),
            "F1", COLORS["muted"]
        )
        pdf.text(MARGIN + 270, pdf.y, 8.6, "Mais recente:", "F2", COLORS["navy"])
        pdf.text(
            MARGIN + 330, pdf.y, 8.6,
            "{}  ({})".format(_dt(result.newest[0]), pdf.trunc(result.newest[1], 8.6, "F1", 160)),
            "F1", COLORS["muted"]
        )
        pdf.y -= 13

    # ---------- 1. Resumo por Categoria / Tipo de Conteúdo ----------
    pdf.bookmark("1. Resumo por Categorias")
    pdf.heading("1. Distribuição de Conteúdo por Categoria")
    y, rh = pdf.y, 13.0
    bar_x, bar_w = MARGIN + 315, USABLE_W - 315 - 2
    pdf.rect(MARGIN, y - 3, USABLE_W, rh, COLORS["navy"])
    for txt, x, al in [
        ("Categoria", MARGIN, "l"),
        ("Tamanho", MARGIN + 150, "r"),
        ("% Espaço", MARGIN + 205, "r"),
        ("Arquivos", MARGIN + 275, "r"),
        ("Proporção Visual", bar_x, "l")
    ]:
        if al == "r":
            pdf.text_right(x, y, 8.2, txt, "F2", COLORS["white"])
        else:
            pdf.text(x, y, 8.2, txt, "F2", COLORS["white"])
    pdf.y -= rh

    for idx, (cat, (sz, cnt)) in enumerate(result.by_cat.items()):
        pdf.ensure(rh + 2)
        y = pdf.y
        shade = (idx % 2 == 1)
        pdf.table_row(y, rh, [
            (pdf.trunc(cat, 8.5, "F1", 130), MARGIN + 12, "l", 8.5, "F1", COLORS["text"]),
            (scanner.human(sz), MARGIN + 150, "r", 8.5, "F1", COLORS["text"]),
            (pct(sz), MARGIN + 205, "r", 8.5, "F1", COLORS["text"]),
            (_num(cnt), MARGIN + 275, "r", 8.5, "F1", COLORS["text"]),
        ], shade=shade)
        pdf.rect(MARGIN + 4, y - 2, 8, 8, color_of(cat))
        pdf.bar(bar_x, y - 2.5, bar_w, 7.5, sz / size_total, color_of(cat))
        pdf.y -= rh
    pdf.y -= 2

    # ---------- Histograma de Modificação por Ano ----------
    years = [yr for yr in sorted(result.year_hist, reverse=True)[:12] if yr > 1990]
    if len(years) > 2:
        pdf.heading("Idade dos Dados — Arquivos por Ano de Modificação", y_gap=10)
        cols = min(len(years), 8)
        col_w = USABLE_W / cols
        for i, yr in enumerate(years):
            x = MARGIN + i * col_w
            q, sz = result.year_hist[yr]
            total_years = max(sum(v[1] for v in result.year_hist.values()), 1)
            share = sz / total_years
            pdf.bar(x + 4, pdf.y, col_w - 8, 4, share, COLORS["navy"])
            pdf.text(x + 4, pdf.y - 3, 7, _num(q), "F2", COLORS["text"])
            pdf.text(x + 4, pdf.y + 6, 7.5, str(yr), "F1", COLORS["muted"])
        pdf.y -= 16

    # ---------- 2. Estrutura de Pastas (Hierarquia em 3 Níveis) ----------
    pdf.bookmark("2. Estrutura de Pastas")
    pdf.heading("2. Estrutura Hierárquica — Pastas de 1º Nível")
    for d in result.top_dirs:
        pdf.ensure(46)
        color = COLORS["navy"]
        pdf.rect(MARGIN + 3, pdf.y - 1.5, 2.5, 9.5, color)
        pdf.text(
            MARGIN + 12, pdf.y, 10.5,
            pdf.trunc(d.name + "/", 10.5, "F2", USABLE_W - 200),
            "F2", COLORS["navy"]
        )
        meta = "{}  ·  {} arquivos  ·  {} do volume".format(
            scanner.human(d.total_size), _num(d.total_files), pct(d.total_size)
        )
        pdf.text_right(PAGE_W - MARGIN, pdf.y, 8.2, meta, "F1", COLORS["muted"])
        pdf.y -= 13
        pdf.bar(MARGIN + 12, pdf.y - 1, USABLE_W - 12, 7, d.total_size / size_total, color)
        pdf.y -= 12

        kids = [k for k in d.children if k.total_size > 0][:25]
        if kids:
            pdf.ensure(10 + len(kids) * 9.5)
            for k in kids:
                pdf.table_row(pdf.y, 9.5, [
                    (pdf.trunc("· " + k.name + "/", 8.2, "F1", 235), MARGIN + 22, "l", 8.2, "F1", COLORS["text"]),
                    (scanner.human(k.total_size), MARGIN + 340, "r", 8.2, "F1", COLORS["text"]),
                    (_num(k.total_files), MARGIN + 460, "r", 8.2, "F1", COLORS["text"]),
                ])
                pdf.y -= 9.5

                # Nível 3: Netos de pastas significativas
                grandkids = [g for g in k.children if g.total_size > 0]
                if d.total_size >= 0.005 * size_total and len(grandkids) > 1 and k.total_size >= 0.002 * size_total:
                    pdf.ensure(min(len(grandkids), 8) * 9 + 8)
                    for g in grandkids[:8]:
                        pdf.table_row(pdf.y, 9.0, [
                            (pdf.trunc("· " + g.name + "/", 7.6, "F1", 215), MARGIN + 34, "l", 7.6, "F1", COLORS["muted"]),
                            (scanner.human(g.total_size), MARGIN + 340, "r", 7.6, "F1", COLORS["muted"]),
                            (_num(g.total_files), MARGIN + 460, "r", 7.6, "F1", COLORS["muted"]),
                        ])
                        pdf.y -= 9.0
                    if len(grandkids) > 8:
                        pdf.table_row(pdf.y, 8.5, [
                            ("· … +{} subpastas adicionais".format(len(grandkids) - 8), MARGIN + 34, "l", 7.6, "F1", COLORS["light"])
                        ])
                        pdf.y -= 8.5
        else:
            pdf.table_row(pdf.y, 9.5, [("· (apenas arquivos nesta pasta)", MARGIN + 22, "l", 8.2, "F1", COLORS["light"])])
            pdf.y -= 9.5
        pdf.y -= 6

    # ---------- 3. Maiores Arquivos Identificados ----------
    pdf.add_page()
    pdf.bookmark("3. Maiores Arquivos")
    pdf.heading("3. Maiores Arquivos (>= {:.0f} MB)".format(result.big_threshold / (1024 * 1024)))
    y = pdf.y
    pdf.rect(MARGIN, y - 3, USABLE_W, 13, COLORS["navy"])
    pdf.text(MARGIN + 4, y, 8.2, "Tamanho", "F2", COLORS["white"])
    pdf.text(MARGIN + 85, y, 8.2, "Localização (Pasta)", "F2", COLORS["white"])
    pdf.text(MARGIN + 275, y, 8.2, "Nome do Arquivo", "F2", COLORS["white"])
    pdf.text_right(PAGE_W - MARGIN - 2, y, 8.2, "Modificado Em", "F2", COLORS["white"])
    pdf.y -= 13

    for i, (sz, rel, mt) in enumerate(result.big_files):
        pdf.ensure(11)
        parent = os.path.dirname(rel)
        base = os.path.basename(rel)
        pdf.table_row(pdf.y, 10.5, [
            (scanner.human(sz), MARGIN + 75, "r", 8.2, "F1", COLORS["text"]),
            (pdf.trunc(parent + "/", 7.6, "F1", 170), MARGIN + 85, "l", 7.6, "F1", COLORS["muted"]),
            (pdf.trunc(base, 8.2, "F1", 175), MARGIN + 275, "l", 8.2, "F1", COLORS["text"]),
        ], shade=(i % 2 == 1))
        pdf.text_right(PAGE_W - MARGIN - 2, pdf.y, 8.2, _dt(mt), "F1", COLORS["muted"])
        pdf.y -= 10.5

    # ---------- 4. Arquivos Soltos na Raiz ----------
    if result.root_files:
        pdf.y -= 8
        pdf.heading("4. Arquivos Soltos na Raiz do Volume", y_gap=10)
        y = pdf.y
        pdf.rect(MARGIN, y - 3, USABLE_W, 13, COLORS["navy"])
        pdf.text(MARGIN + 4, y, 8.2, "Tamanho", "F2", COLORS["white"])
        pdf.text(MARGIN + 80, y, 8.2, "Nome do Arquivo", "F2", COLORS["white"])
        pdf.text_right(PAGE_W - MARGIN - 2, y, 8.2, "Modificado Em", "F2", COLORS["white"])
        pdf.y -= 13
        for i, (sz, name, mt) in enumerate(result.root_files):
            pdf.ensure(11)
            pdf.table_row(pdf.y, 10.5, [
                (scanner.human(sz), MARGIN + 72, "r", 8.2, "F1", COLORS["text"]),
                (pdf.trunc(name, 8.2, "F1", USABLE_W - 140), MARGIN + 80, "l", 8.2, "F1", COLORS["text"]),
            ], shade=(i % 2 == 1))
            pdf.text_right(PAGE_W - MARGIN - 2, pdf.y, 8.2, _dt(mt), "F1", COLORS["muted"])
            pdf.y -= 10.5

    # ---------- 5. Top Extensões ----------
    pdf.add_page()
    pdf.bookmark("5. Ranking de Extensões")
    pdf.heading("5. Top {} Extensões Mais Frequentes".format(len(result.by_ext)))
    y = pdf.y
    pdf.rect(MARGIN, y - 3, USABLE_W, 13, COLORS["navy"])
    for txt, x, al in [
        ("Extensão", MARGIN + 4, "l"),
        ("Tamanho Total", MARGIN + 150, "r"),
        ("Total Arquivos", MARGIN + 250, "r"),
        ("% do Volume", MARGIN + 350, "r")
    ]:
        if al == "r":
            pdf.text_right(x, y, 8.2, txt, "F2", COLORS["white"])
        else:
            pdf.text(x, y, 8.2, txt, "F2", COLORS["white"])
    pdf.y -= 13

    for i, (ext, (sz, cnt)) in enumerate(result.by_ext.items()):
        pdf.ensure(11)
        pdf.table_row(pdf.y, 10.5, [
            (ext, MARGIN + 4, "l", 8.2, "F1", COLORS["text"]),
            (scanner.human(sz), MARGIN + 150, "r", 8.2, "F1", COLORS["text"]),
            (_num(cnt), MARGIN + 250, "r", 8.2, "F1", COLORS["text"]),
            (pct(sz), MARGIN + 350, "r", 8.2, "F1", COLORS["text"]),
        ], shade=(i % 2 == 1))
        pdf.y -= 10.5

    # ---------- 6. Detecção de Duplicados ----------
    if result.dup_mode != "off":
        pdf.y -= 8
        pdf.bookmark("6. Arquivos Duplicados")
        pdf.heading("6. Diagnóstico de Arquivos Duplicados", y_gap=10)
        waste, ngroups = result.dup_totals
        mode_txt = {
            "rapido": "Nome + Tamanho idênticos",
            "parcial": "Nome + Tamanho + Hash parcial (128 KB)",
            "completo": "Hash SHA-256 integral"
        }.get(result.dup_mode, "")

        pdf.text(
            MARGIN, pdf.y, 8.6,
            "Critério: {} · {} grupos com desperdício estimado de {} em {} cópias".format(
                mode_txt, _num(ngroups), scanner.human(waste),
                _num(sum(len(g["files"]) - 1 for g in result.dup_groups))
            ),
            "F1", COLORS["muted"]
        )
        pdf.y -= 13
        y = pdf.y
        pdf.rect(MARGIN, y - 3, USABLE_W, 13, COLORS["navy"])
        for txt, x, al in [
            ("Tamanho", MARGIN + 60, "r"),
            ("Cópias", MARGIN + 100, "r"),
            ("Desperdício", MARGIN + 180, "r"),
            ("Arquivo e Localização das Cópias", MARGIN + 195, "l")
        ]:
            if al == "r":
                pdf.text_right(x, y, 8.2, txt, "F2", COLORS["white"])
            else:
                pdf.text(x, y, 8.2, txt, "F2", COLORS["white"])
        pdf.y -= 13

        if result.dup_groups:
            for i, g in enumerate(result.dup_groups[:40]):
                pdf.ensure(11)
                pdf.table_row(pdf.y, 10.5, [
                    (scanner.human(g["size"]), MARGIN + 60, "r", 8.2, "F1", COLORS["text"]),
                    (_num(len(g["files"])), MARGIN + 100, "r", 8.2, "F1", COLORS["text"]),
                    (scanner.human(g["waste"]), MARGIN + 180, "r", 8.2, "F2", COLORS["text"]),
                    (pdf.trunc(g["name"], 8.2, "F1", USABLE_W - 200), MARGIN + 195, "l", 8.2, "F1", COLORS["text"]),
                ], shade=(i % 2 == 1))
                pdf.y -= 10.5
                for j, f in enumerate(g["files"][1:6], 1):
                    pdf.ensure(9.5)
                    pdf.text(
                        MARGIN + 205, pdf.y, 7.4,
                        "cópia {}: {}".format(j, pdf.trunc(f, 7.4, "F1", USABLE_W - 215)),
                        "F1", COLORS["muted"]
                    )
                    pdf.y -= 9.0
                if len(g["files"]) > 6:
                    pdf.text(
                        MARGIN + 205, pdf.y, 7.4,
                        "… +{} cópias adicionais".format(len(g["files"]) - 6),
                        "F1", COLORS["light"]
                    )
                    pdf.y -= 9.0
        else:
            pdf.table_row(pdf.y, 10, [("Nenhuma duplicata encontrada.", MARGIN + 4, "l", 8.2, "F1", COLORS["muted"])])
            pdf.y -= 10

    # ---------- 7. Candidatos à Limpeza ----------
    if result.cleanup:
        pdf.y -= 8
        pdf.bookmark("7. Oportunidades de Limpeza")
        pdf.heading("7. Itens Candidatos à Limpeza e Otimização", y_gap=10)
        y = pdf.y
        pdf.rect(MARGIN, y - 3, USABLE_W, 13, COLORS["navy"])
        pdf.text(MARGIN + 4, y, 8.2, "Categoria de Descarte / Otimização", "F2", COLORS["white"])
        pdf.text_right(MARGIN + 260, y, 8.2, "Espaço Ocupado", "F2", COLORS["white"])
        pdf.text_right(MARGIN + 350, y, 8.2, "Quantidade", "F2", COLORS["white"])
        pdf.y -= 13

        for i, (label, (sz, cnt)) in enumerate(result.cleanup.items()):
            pdf.ensure(11)
            pdf.table_row(pdf.y, 10.5, [
                (label, MARGIN + 4, "l", 8.2, "F1", COLORS["text"]),
                (scanner.human(sz), MARGIN + 260, "r", 8.2, "F1", COLORS["text"]),
                (_num(cnt), MARGIN + 350, "r", 8.2, "F1", COLORS["text"]),
            ], shade=(i % 2 == 1))
            pdf.y -= 10.5

        if result.cleanup_note:
            pdf.y -= 2
            pdf.text(MARGIN, pdf.y, 7.8, "Observação: {}".format(result.cleanup_note), "F1", COLORS["light"])
            pdf.y -= 10

    note = footer_note or (
        "Analista & Organizador de Arquivos · Método: varredura lógica estrutural · "
        "Espaço total indexado: {}.".format(scanner.human(result.total_size))
    )
    pdf.save(out_path, footer_note=note)
    return out_path
