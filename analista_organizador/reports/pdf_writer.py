"""Escritor de PDF nativo vetorial em Python puro (sem dependências externas).

Suporta: páginas A4, tipografia padrão Helvetica/Helvetica-Bold com WinAnsiEncoding
(acentos pt-BR corretos), retângulos coloridos, texto alinhado, barras de proporção,
tabelas zebradas, quebras de página e sumário/bookmarks clicáveis na barra lateral do leitor.
"""

import io
from typing import Dict, List, Optional, Tuple

PAGE_W, PAGE_H = 595.27, 841.89  # A4 em pontos tipográficos
MARGIN = 34.0
USABLE_W = PAGE_W - 2 * MARGIN

# Largura média estimada por caractere (fração do tamanho da fonte)
AVG_W = {"F1": 0.517, "F2": 0.548}   # F1=Helvetica, F2=Helvetica-Bold

COLORS: Dict[str, Tuple[float, float, float]] = {
    "navy": (0.118, 0.227, 0.541),
    "text": (0.122, 0.173, 0.216),
    "muted": (0.420, 0.443, 0.502),
    "light": (0.612, 0.639, 0.686),
    "card_bg": (0.976, 0.980, 0.984),
    "row_alt": (0.973, 0.980, 0.988),
    "line": (0.945, 0.961, 0.976),
    "bar_bg": (0.933, 0.949, 0.969),
    "white": (1.0, 1.0, 1.0),
}


def _esc_bytes(s: str) -> bytes:
    """Codifica texto em cp1252/WinAnsi e escapa caracteres reservados para stream PDF."""
    b = s.encode("cp1252", errors="replace")
    out = bytearray()
    for c in b:
        if c in (0x28, 0x29, 0x5C):  # ( ) \
            out += b"\\"
        out.append(c)
    return bytes(out)


def _fmt_color(rgb: Tuple[float, float, float]) -> str:
    return "{:.3f} {:.3f} {:.3f}".format(*rgb)


class PDF:
    """Gerador e montador de documentos PDF vetoriais."""

    def __init__(self):
        self.pages: List[List[str]] = []
        self.cur: List[str] = []
        self.y: float = PAGE_H - MARGIN
        self.bookmarks: List[Tuple[str, int, float]] = []  # [(título, índice_página, y_top)]

    # ---- Controle de Páginas e Dimensões ---------------------------------
    def add_page(self):
        if self.cur:
            self.pages.append(self.cur)
        self.cur = []
        self.y = PAGE_H - MARGIN

    def bookmark(self, title: str):
        """Registra nó no índice/sumário clicável do PDF."""
        pidx = len(self.pages)
        self.bookmarks.append((title, pidx, self.y + 6))

    def ensure(self, needed: float) -> bool:
        """Gera nova página automaticamente se o espaço restante for insuficiente."""
        if self.y - needed < MARGIN + 14:
            self.add_page()
            return True
        return False

    def _width(self, s: str, size: float, font: str) -> float:
        return len(s) * AVG_W.get(font, 0.52) * size

    def trunc(self, s: str, size: float, font: str, max_w: float) -> str:
        """Trunca a string com reticências para assegurar largura máxima."""
        if self._width(s, size, font) <= max_w:
            return s
        keep = max(1, int(max_w / (AVG_W.get(font, 0.52) * size)) - 1)
        return s[:keep] + "..."

    # ---- Primitivas Gráficas Vetoriais -----------------------------------
    def rect(self, x: float, y: float, w: float, h: float, color: Tuple[float, float, float], stroke: bool = False):
        self.cur.append("{} rg {:g} {:g} {:g} {:g} re {}".format(
            _fmt_color(color), x, y, w, h, "S" if stroke else "f"))

    def text(self, x: float, y: float, size: float, s: str, font: str = "F1", color: Optional[Tuple[float, float, float]] = None):
        c = color or COLORS["text"]
        self.cur.append("BT {c} rg /{f} {sz:g} Tf 1 0 0 1 {x:g} {y:g} Tm ({t}) Tj ET".format(
            c=_fmt_color(c), f=font, sz=size, x=x, y=y,
            t=_esc_bytes(s).decode("latin-1")))

    def text_right(self, x_right: float, y: float, size: float, s: str, font: str = "F1", color: Optional[Tuple[float, float, float]] = None):
        w = self._width(s, size, font)
        self.text(x_right - w, y, size, s, font, color)

    # ---- Componentes de Alto Nível --------------------------------------
    def heading(self, title: str, y_gap: float = 14.0):
        self.ensure(30 + y_gap)
        self.y -= y_gap
        self.rect(MARGIN, self.y - 2, USABLE_W, 0.8, COLORS["navy"])
        self.text(MARGIN, self.y + 4, 12.5, title, "F2", COLORS["navy"])
        self.y -= 14

    def cards(self, items: List[Tuple[str, str]]):
        """Renderiza cartões estatísticos no topo: items = [(valor, rótulo), ...]"""
        n = len(items)
        gap = 6.0
        w = (USABLE_W - gap * (n - 1)) / n
        h = 40.0
        self.ensure(h + 6)
        for i, (val, label) in enumerate(items):
            x = MARGIN + i * (w + gap)
            y = self.y - h
            self.rect(x, y, w, h, COLORS["card_bg"])
            self.rect(x, y, w, h, COLORS["line"], stroke=True)
            self.text(x + 8, y + 22, 11.5, self.trunc(val, 11.5, "F2", w - 14), "F2", COLORS["navy"])
            self.text(x + 8, y + 8, 6.6, self.trunc(label.upper(), 6.6, "F1", w - 14), "F1", COLORS["muted"])
        self.y -= h + 8

    def table_row(self, y: float, heights: float, cells: List[Tuple], shade: bool = False):
        """Renderiza uma linha de tabela estruturada. cells = [(texto, x, align, size, font, color)]"""
        if shade:
            self.rect(MARGIN, y - 3.5, USABLE_W, heights, COLORS["row_alt"])
        for txt, x, align, size, font, color in cells:
            if align == "r":
                self.text_right(x, y, size, txt, font, color)
            else:
                self.text(x, y, size, txt, font, color)

    def bar(self, x: float, y: float, w: float, h: float, frac: float, color: Tuple[float, float, float]):
        """Renderiza barra horizontal proporcional com fundo neutro."""
        self.rect(x, y, w, h, COLORS["bar_bg"])
        if frac > 0:
            self.rect(x, y, max(1.5, w * min(1.0, frac)), h, color)

    # ---- Serialização e Escrita Final do Arquivo -------------------------
    def save(self, path: str, footer_note: str = ""):
        total = len(self.pages) + (1 if self.cur else 0)
        pages_data = self.pages + ([self.cur] if self.cur else [])
        self.cur = []

        # Adicionar rodapés com paginação automática
        for i, ops in enumerate(pages_data, 1):
            ops.append("BT {} rg /F1 7 Tf 1 0 0 1 {:g} {:g} Tm ({}) Tj ET".format(
                _fmt_color(COLORS["muted"]), PAGE_W - MARGIN - 60,
                MARGIN - 12, _esc_bytes("Página %d de %d" % (i, total)).decode("latin-1")))
            if footer_note:
                ops.append("BT {} rg /F1 7 Tf 1 0 0 1 {:g} {:g} Tm ({}) Tj ET".format(
                    _fmt_color(COLORS["light"]), MARGIN, MARGIN - 12,
                    _esc_bytes(self.trunc(footer_note, 7, "F1", USABLE_W - 80)).decode("latin-1")))

        # Construir objetos estruturais do padrão PDF
        objs = []
        n_pages = total
        n_bm = len(self.bookmarks)
        outline_obj = 5 + 2 * n_pages

        objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        kids = " ".join("{} 0 R".format(5 + 2 * i) for i in range(total))
        objs.append(("<< /Type /Pages /Kids [{}] /Count {} >>".format(kids, total)).encode("latin-1"))
        objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")

        for i, ops in enumerate(pages_data, 1):
            content = "\n".join(ops).encode("latin-1", errors="replace")
            objs.append(("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {:g} {:g}] "
                         "/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
                         "/Contents {} 0 R >>".format(PAGE_W, PAGE_H, 4 + 2 * i)).encode("latin-1"))
            objs.append(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content))

        if n_bm:
            objs[0] = ("<< /Type /Catalog /Pages 2 0 R /Outlines {} 0 R "
                       "/PageMode /UseOutlines >>".format(outline_obj)).encode("latin-1")
            first = outline_obj + 1
            last = outline_obj + n_bm
            objs.append(("<< /Type /Outlines /First {} 0 R /Last {} 0 R "
                         "/Count {} >>".format(first, last, n_bm)).encode("latin-1"))
            for j, (title, pidx, ytop) in enumerate(self.bookmarks):
                item_num = first + j
                parts = [
                    "<< /Title ({})".format(_esc_bytes(title).decode("latin-1")),
                    "/Parent {} 0 R".format(outline_obj),
                    "/Dest [{} 0 R /XYZ 0 {:g} 0]".format(5 + 2 * pidx, PAGE_H - ytop)
                ]
                if j > 0:
                    parts.append("/Prev {} 0 R".format(item_num - 1))
                if j < n_bm - 1:
                    parts.append("/Next {} 0 R".format(item_num + 1))
                parts.append("/Count 0 >>")
                objs.append(" ".join(parts).encode("latin-1"))

        buf = io.BytesIO()
        buf.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for num, obj in enumerate(objs, 1):
            offsets.append(buf.tell())
            buf.write(b"%d 0 obj\n" % num)
            buf.write(obj)
            buf.write(b"\nendobj\n")
        xref_pos = buf.tell()
        buf.write(b"xref\n0 %d\n" % (len(objs) + 1))
        buf.write(b"0000000000 65535 f \n")
        for off in offsets:
            buf.write(b"%010d 00000 n \n" % off)
        buf.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
                  % (len(objs) + 1, xref_pos))

        with open(path, "wb") as f:
            f.write(buf.getvalue())
