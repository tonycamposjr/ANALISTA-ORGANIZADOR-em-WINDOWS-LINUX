"""Exportação do inventário detalhado de arquivos em formato CSV (compatível com Excel e LibreOffice)."""

import csv
import os
import time
from typing import Callable, Optional

from ..core.categories import category_of
from ..core.scanner import ScanResult, human


def write_csv(result: ScanResult, path: str, progress: Optional[Callable[[int], None]] = None) -> int:
    """Gera inventário de todos os arquivos indexados no volume em arquivo CSV delimitado por ';'.

    Utiliza codificação UTF-8 com BOM (utf-8-sig) para abertura nativa e sem distorções no Excel.
    """
    root = result.root
    n = 0
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow([
            "caminho", "pasta", "arquivo", "tamanho_bytes",
            "tamanho_legivel", "categoria", "extensao",
            "modificado_em", "duplicado_grupo"
        ])

        for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
            dirnames[:] = [
                d for d in dirnames if d not in (
                    "$RECYCLE.BIN", "System Volume Information", ".Trash-1000", ".git"
                ) and not d.startswith(".")
            ]

            for fn in filenames:
                p = os.path.join(dirpath, fn)
                try:
                    st = os.stat(p)
                except OSError:
                    continue

                ext = os.path.splitext(fn)[1].lower()
                rel = os.path.relpath(p, root)
                w.writerow([
                    rel,
                    os.path.dirname(rel),
                    fn,
                    st.st_size,
                    human(st.st_size),
                    category_of(ext),
                    ext,
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)),
                    result.dup_map.get(p, ""),
                ])
                n += 1
                if progress and n % 5000 == 0:
                    progress(n)

    return n
