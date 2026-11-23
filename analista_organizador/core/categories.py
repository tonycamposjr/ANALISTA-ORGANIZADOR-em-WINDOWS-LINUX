"""Categorização de arquivos por extensão e mapeamento cromático para relatórios."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Dicionário padrão unificado combinando as regras de análise e organização
DEFAULT_CATEGORIES: Dict[str, List[str]] = {
    "Imagens": [
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp",
        ".svg", ".ico", ".heic", ".raw", ".cr2", ".nef"
    ],
    "Videos": [
        ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v",
        ".mpg", ".mpeg", ".3gp", ".ts", ".vob"
    ],
    "Audio": [
        ".mp3", ".wav", ".flac", ".ogg", ".m4a", ".wma", ".aac", ".mid",
        ".midi", ".opus"
    ],
    "Documentos": [
        ".pdf", ".doc", ".docx", ".txt", ".odt", ".rtf", ".md", ".wri", ".one"
    ],
    "Planilhas": [
        ".xls", ".xlsx", ".csv", ".ods"
    ],
    "Apresentacoes": [
        ".ppt", ".pptx", ".odp"
    ],
    "Compactados": [
        ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tgz",
        ".iso", ".cab", ".arj", ".lzh"
    ],
    "Instaladores": [
        ".exe", ".msi", ".msu", ".apk", ".deb", ".rpm", ".appx", ".dmg", ".appimage"
    ],
    "Codigo": [
        ".py", ".js", ".ts", ".html", ".htm", ".css", ".java", ".c", ".cpp",
        ".h", ".cs", ".php", ".sh", ".bat", ".cmd", ".ps1", ".json", ".xml",
        ".yml", ".yaml", ".sql", ".ini", ".cfg", ".conf", ".jar", ".dll",
        ".so", ".ipynb", ".lua", ".pl", ".vbs", ".go", ".rs", ".rb"
    ],
    "Fontes": [
        ".ttf", ".otf", ".woff", ".woff2", ".fon"
    ],
    "Design": [
        ".psd", ".ai", ".xd", ".fig", ".sketch", ".cdr"
    ],
    "Maquinas Virtuais": [
        ".vdi", ".vmdk", ".vmem", ".vhd", ".vhdx", ".ova", ".ovf", ".vmx",
        ".vmsd", ".vmsn", ".vmss", ".nvram"
    ],
    "Banco de Dados": [
        ".db", ".sqlite", ".sqlite3", ".mdb", ".accdb", ".bak", ".mdf"
    ],
}

# Paleta cromática RGB (normalizada em 0..1) para gráficos e relatórios PDF
CATEGORY_COLORS: Dict[str, Tuple[float, float, float]] = {
    "Imagens": (0.145, 0.388, 0.922),          # Azul vivo
    "Videos": (0.486, 0.227, 0.929),           # Roxo
    "Audio": (0.859, 0.153, 0.467),            # Magenta / Rosa escuro
    "Documentos": (0.024, 0.588, 0.412),       # Verde Esmeralda
    "Planilhas": (0.133, 0.694, 0.298),        # Verde Claro
    "Apresentacoes": (0.918, 0.450, 0.120),    # Laranja Intenso
    "Compactados": (0.851, 0.467, 0.024),      # Laranja Queimado
    "Instaladores": (0.031, 0.569, 0.698),     # Azul Petróleo / Ciano
    "Codigo": (0.396, 0.639, 0.027),           # Verde Oliva
    "Fontes": (0.576, 0.200, 0.918),           # Violeta
    "Design": (0.918, 0.235, 0.525),           # Rosa Choque
    "Maquinas Virtuais": (0.725, 0.110, 0.110),# Vermelho Carmim
    "Banco de Dados": (0.918, 0.345, 0.024),   # Âmbar
    "Outros": (0.420, 0.443, 0.502),           # Cinza Neutro
    "Sem extensao": (0.612, 0.639, 0.686),     # Cinza Claro
}

# Aliases para compatibilidade retroativa com os projetos de origem
CATEGORIAS_PADRAO = DEFAULT_CATEGORIES
CATEGORIES = {k: set(v) for k, v in DEFAULT_CATEGORIES.items()}

# Cache base padrão imutável extensão -> categoria
_CACHE_DEFAULT_EXT_TO_CAT: Dict[str, str] = {}
for _cat, _exts in DEFAULT_CATEGORIES.items():
    for _ext in _exts:
        _CACHE_DEFAULT_EXT_TO_CAT[_ext.lower()] = _cat

# Cache customizado opcional
_CUSTOM_CACHE_EXT_TO_CAT: Optional[Dict[str, str]] = None


def carregar_categorias(caminho_config: Optional[str] = None) -> Dict[str, List[str]]:
    """Carrega categorias de um arquivo JSON; se nulo ou inválido, retorna as padrão."""
    if not caminho_config:
        return {k: list(v) for k, v in DEFAULT_CATEGORIES.items()}

    p = Path(caminho_config)
    if not p.is_file():
        return {k: list(v) for k, v in DEFAULT_CATEGORIES.items()}

    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, dict):
            resultado = {}
            for cat, exts in data.items():
                if isinstance(exts, list):
                    resultado[cat] = [
                        ext.lower() if ext.startswith(".") else f".{ext.lower()}"
                        for ext in exts
                    ]
            return resultado

    return {k: list(v) for k, v in DEFAULT_CATEGORIES.items()}


def ativar_categorias_customizadas(categorias: Optional[Dict[str, List[str]]]) -> None:
    """Define globalmente um mapeamento de categorias ativas ou reseta para o padrão se None."""
    global _CUSTOM_CACHE_EXT_TO_CAT
    if not categorias:
        _CUSTOM_CACHE_EXT_TO_CAT = None
        return

    novo_cache: Dict[str, str] = {}
    for cat, exts in categorias.items():
        for ext in exts:
            novo_cache[ext.lower()] = cat
    _CUSTOM_CACHE_EXT_TO_CAT = novo_cache


def salvar_categorias(caminho_destino: str, categorias: Dict[str, List[str]]) -> None:
    """Exporta um dicionário de categorias para arquivo JSON formatado."""
    p = Path(caminho_destino)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(categorias, f, ensure_ascii=False, indent=2)


def category_of(ext: Optional[str], categories: Optional[Dict[str, List[str]]] = None) -> str:
    """Retorna o nome da categoria associada à extensão informada."""
    if not ext:
        return "Sem extensao"

    ext = ext.lower().strip()
    if not ext.startswith("."):
        ext = f".{ext}"

    if categories is not None:
        for cat, exts in categories.items():
            if ext in exts or ext.lower() in [e.lower() for e in exts]:
                return cat
        return "Outros"

    if _CUSTOM_CACHE_EXT_TO_CAT is not None:
        return _CUSTOM_CACHE_EXT_TO_CAT.get(ext, "Outros")

    return _CACHE_DEFAULT_EXT_TO_CAT.get(ext, "Outros")


def categoria_por_extensao(extensao: str, categorias: Dict[str, List[str]]) -> str:
    """Função compatível com Projeto B para categorizar por extensão."""
    return category_of(extensao, categories=categorias)


def color_of(category: str) -> Tuple[float, float, float]:
    """Retorna a tupla RGB (0..1) associada à categoria."""
    return CATEGORY_COLORS.get(category, CATEGORY_COLORS["Outros"])
