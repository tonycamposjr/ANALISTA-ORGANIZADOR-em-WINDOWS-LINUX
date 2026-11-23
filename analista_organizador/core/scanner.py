"""Varredura recursiva de armazenamento: análise de capacidade, extensões, idade e duplicatas."""

import hashlib
import os
import shutil
import time
from collections import defaultdict
from typing import Callable, Dict, List, Optional, Tuple

from .categories import category_of

SKIP_DIRS = {
    "$RECYCLE.BIN", "System Volume Information", ".Trash-1000",
    ".Trash", ".Trash-0", ".git", ".svn"
}

TEMP_EXTS = {".tmp", ".temp", ".bak", ".old", ".dmp", ".log"}
SYSJUNK_NAMES = {"desktop.ini", "thumbs.db", ".ds_store"}

DUP_MODES = ("off", "rapido", "parcial", "completo")


def human(n: float | int) -> str:
    """Formata bytes em texto legível: 93,2 GB, 500 KB."""
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if n < 1024 or unit == "PB":
            if unit == "B":
                return "{:,.0f} {}".format(n, unit).replace(",", ".")
            return ("{:,.1f} {}".format(n, unit)
                    .replace(",", "X").replace(".", ",").replace("X", "."))
        n /= 1024.0
    return "0 B"


def human_time(secs: int | float) -> str:
    """Formata tempo em segundos para formato amigável: 1h20m, 45s."""
    secs = int(secs)
    if secs >= 3600:
        return "{:d}h{:02d}m".format(secs // 3600, (secs % 3600) // 60)
    if secs >= 60:
        return "{:d}m{:02d}s".format(secs // 60, secs % 60)
    return "{}s".format(max(0, secs))


def _mtime_str(ts: float) -> str:
    return time.strftime("%d/%m/%Y", time.localtime(ts))


class ScanProgress:
    """Callback de progresso com cálculo de fração estimada e ETA."""

    def __init__(self, callback: Optional[Callable] = None, root: Optional[str] = None):
        self.callback = callback
        self.files = 0
        self.bytes = 0
        self._last_report = 0.0
        self._start = time.monotonic()
        self._total_bytes = 0
        if root:
            try:
                self._total_bytes = max(shutil.disk_usage(root).used, 1)
            except OSError:
                self._total_bytes = 0

    def tick(self, size: int):
        self.files += 1
        self.bytes += size
        now = time.monotonic()
        if self.callback and (now - self._last_report > 0.25):
            self._last_report = now
            frac = (self.bytes / self._total_bytes) if self._total_bytes else 0.0
            frac = min(frac, 0.99)
            eta = ""
            if frac > 0.02:
                secs = (now - self._start) / frac * (1.0 - frac)
                eta = "resta ~{}".format(human_time(int(secs)))
            self.callback(self.files, self.bytes, frac, eta)


def _fingerprint_parcial(path: str, size: int) -> str:
    """Hash SHA-256 dos primeiros 64KB + últimos 64KB + tamanho do arquivo."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        head = f.read(65536)
        h.update(head)
        if size > 65536:
            f.seek(max(size - 65536, 65536))
            h.update(f.read())
    h.update(str(size).encode("utf-8"))
    return h.hexdigest()


def _fingerprint_completo(path: str) -> str:
    """Hash SHA-256 integral do arquivo lendo em blocos de 1MB."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class DirInfo:
    """Informações agregadas de diretório."""

    def __init__(self):
        self.name: str = ""
        self.total_size: int = 0
        self.total_files: int = 0
        self.children: List["DirInfo"] = []


class ScanResult:
    """Resultado detalhado consolidado da varredura."""

    def __init__(self):
        self.root: str = ""
        self.total_size: int = 0
        self.total_files: int = 0
        self.total_dirs: int = 0
        self.by_cat: Dict[str, List[int]] = {}       # cat -> [tamanho, contagem]
        self.by_ext: Dict[str, List[int]] = {}       # ext -> [tamanho, contagem]
        self.big_files: List[Tuple[int, str, float]] = []  # [(tamanho, rel_path, mtime)]
        self.root_files: List[Tuple[int, str, float]] = [] # [(tamanho, nome, mtime)]
        self.top_dirs: List[DirInfo] = []
        self.big_threshold: int = 50 * 1024 * 1024
        self.dup_mode: str = "rapido"
        self.dup_groups: List[Dict] = []             # [{'name','size','waste','files':[rel,...]}]
        self.dup_totals: Tuple[int, int] = (0, 0)    # (desperdício_bytes, total_grupos)
        self.dup_map: Dict[str, int] = {}            # abs_path -> índice do grupo
        self.year_hist: Dict[int, List[int]] = {}    # ano -> [qtd, tamanho]
        self.oldest: Optional[Tuple[float, str]] = None
        self.newest: Optional[Tuple[float, str]] = None
        self.cleanup: Dict[str, List[int]] = {}      # rótulo -> [tamanho, qtd]
        self.cleanup_note: str = ""
        self.dup_scanned: int = 0


def scan(
    root: str,
    progress: Optional[ScanProgress] = None,
    big_threshold: int = 50 * 1024 * 1024,
    dup_mode: str = "rapido",
    categories: Optional[Dict[str, List[str]]] = None
) -> ScanResult:
    """Executa a varredura recursiva de `root` e produz um ScanResult completo."""
    if dup_mode not in DUP_MODES:
        dup_mode = "rapido"
    if progress is None:
        progress = ScanProgress(root=root)

    res = ScanResult()
    res.root = os.path.abspath(root)
    res.big_threshold = big_threshold
    res.dup_mode = dup_mode

    by_cat = defaultdict(lambda: [0, 0])
    by_ext = defaultdict(lambda: [0, 0])
    big_files = []
    year_hist = defaultdict(lambda: [0, 0])
    oldest = None
    newest = None
    cleanup = defaultdict(lambda: [0, 0])
    small = [0, 0]                       # [qtd, bytes] de arquivos < 1KB
    zero = 0
    dir_size = defaultdict(int)
    dir_count = defaultdict(int)
    dir_map = {}
    children_map = defaultdict(list)
    top_paths = []
    cand = defaultdict(list)             # (nome.lower(), size) -> [abs paths]
    cand_names = {}                      # (nome.lower(), size) -> nome real
    size_index = defaultdict(list)       # size -> [abs paths]
    dup_scanned = [0]                    # bytes lidos em modo de hash

    for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        rel = os.path.relpath(dirpath, root)
        is_root = (rel == ".")
        info = DirInfo()
        info.name = os.path.basename(dirpath) or dirpath
        dir_map[dirpath] = info

        if not is_root:
            parent = os.path.dirname(dirpath)
            children_map[parent].append(dirpath)
            res.total_dirs += 1
        else:
            top_paths = [os.path.join(root, d) for d in dirnames]

        for fn in filenames:
            path = os.path.join(dirpath, fn)
            try:
                st = os.stat(path)
                size = st.st_size
                mt = st.st_mtime
            except OSError:
                continue

            ext = os.path.splitext(fn)[1].lower()
            year = time.localtime(mt).tm_year
            res.total_files += 1
            res.total_size += size
            cat = category_of(ext, categories=categories)
            by_cat[cat][0] += size
            by_cat[cat][1] += 1
            key = ext if ext else "(sem extensao)"
            by_ext[key][0] += size
            by_ext[key][1] += 1
            dir_size[dirpath] += size
            dir_count[dirpath] += 1
            year_hist[year][0] += 1
            year_hist[year][1] += size

            if oldest is None or mt < oldest[0]:
                oldest = (mt, os.path.relpath(path, root))
            if newest is None or mt > newest[0]:
                newest = (mt, os.path.relpath(path, root))

            if size >= big_threshold:
                big_files.append((size, os.path.relpath(path, root), mt))

            if size < 1024:
                small[0] += 1
                small[1] += size
                if size == 0:
                    zero += 1

            if ext in TEMP_EXTS:
                cleanup["Temporarios (.tmp/.bak/.old/.dmp)"][0] += size
                cleanup["Temporarios (.tmp/.bak/.old/.dmp)"][1] += 1
            if fn.lower() in SYSJUNK_NAMES:
                cleanup["desktop.ini / Thumbs.db / .DS_Store"][0] += size
                cleanup["desktop.ini / Thumbs.db / .DS_Store"][1] += 1
            if ext == ".vmem":
                cleanup["Estados de VM salvos (.vmem)"][0] += size
                cleanup["Estados de VM salvos (.vmem)"][1] += 1
            if ext in (".exe", ".msi", ".msu"):
                cleanup["Instaladores (.exe/.msi)"][0] += size
                cleanup["Instaladores (.exe/.msi)"][1] += 1

            if dup_mode in ("rapido", "parcial", "completo") and size > 0:
                k = (fn.lower(), size)
                cand[k].append(path)
                cand_names.setdefault(k, fn)
                size_index[size].append(path)

            progress.tick(size)

    # ---------------- Detecção de Duplicatas ----------------
    dup_groups = []
    if dup_mode == "rapido":
        for k, paths in cand.items():
            if len(paths) > 1:
                g = {
                    "name": cand_names[k],
                    "size": k[1],
                    "waste": k[1] * (len(paths) - 1),
                    "files": [os.path.relpath(p, res.root) for p in paths]
                }
                dup_groups.append(g)
    elif dup_mode in ("parcial", "completo"):
        cand_paths = set()
        for k, paths in cand.items():
            if len(paths) > 1:
                cand_paths.update(paths)
        for size, paths in size_index.items():
            if size >= 1024 * 1024 and len(paths) > 1:
                cand_paths.update(paths)

        by_hash = defaultdict(list)
        for p in cand_paths:
            try:
                st = os.stat(p)
                if dup_mode == "parcial":
                    fp = _fingerprint_parcial(p, st.st_size)
                else:
                    fp = _fingerprint_completo(p)
                dup_scanned[0] += st.st_size
                by_hash[fp].append(p)
            except OSError:
                continue

        for paths in by_hash.values():
            if len(paths) > 1:
                size = os.path.getsize(paths[0])
                dup_groups.append({
                    "name": os.path.basename(paths[0]),
                    "size": size,
                    "waste": size * (len(paths) - 1),
                    "files": [os.path.relpath(p, res.root) for p in paths]
                })

    dup_groups.sort(key=lambda g: -g["waste"])
    total_waste = sum(g["waste"] for g in dup_groups)
    res.dup_groups = dup_groups[:60]
    res.dup_totals = (total_waste, len(dup_groups))

    for i, g in enumerate(res.dup_groups):
        for f in g["files"]:
            res.dup_map[os.path.join(res.root, f)] = i + 1

    if small[0]:
        cleanup["Arquivos pequenos (< 1 KB)"][0] += small[1]
        cleanup["Arquivos pequenos (< 1 KB)"][1] += small[0]

    res.cleanup = dict(sorted(cleanup.items(), key=lambda kv: -kv[1][0]))
    res.cleanup_note = ("{} arquivos com 0 bytes".format(zero) if zero else "")
    res.dup_scanned = dup_scanned[0]

    # ---------------- Tamanhos Recursivos em Árvore ----------------
    memo = {}

    def rsize(path):
        if path in memo:
            return memo[path]
        total = dir_size.get(path, 0)
        for ch in children_map.get(path, []):
            total += rsize(ch)
        memo[path] = total
        return total

    def rcount(path):
        n = dir_count.get(path, 0)
        for ch in children_map.get(path, []):
            n += rcount(ch)
        return n

    for path in dir_map:
        info = dir_map[path]
        info.total_size = rsize(path)
        info.total_files = rcount(path)
        info.children = [
            dir_map[c] for c in sorted(children_map.get(path, []), key=lambda c: -rsize(c))
        ]

    res.top_dirs = sorted((dir_map[p] for p in top_paths), key=lambda i: -i.total_size)
    res.by_cat = dict(sorted(by_cat.items(), key=lambda kv: -kv[1][0]))
    res.by_ext = dict(sorted(by_ext.items(), key=lambda kv: -kv[1][0])[:40])
    res.big_files = sorted(big_files, reverse=True)[:40]
    res.year_hist = dict(sorted(year_hist.items(), reverse=True))
    res.oldest = oldest
    res.newest = newest
    res.root_files = []

    try:
        for fn in os.listdir(root):
            p = os.path.join(root, fn)
            if os.path.isfile(p):
                try:
                    st = os.stat(p)
                    res.root_files.append((st.st_size, fn, st.st_mtime))
                except OSError:
                    pass
    except OSError:
        pass

    res.root_files.sort(reverse=True)
    res.root_files = res.root_files[:15]
    return res
