"""Analista & Organizador de Arquivos.

Sistema unificado de análise de armazenamento, inventário em PDF/CSV,
organização inteligente por categorias e auditoria reversa (rollback).
"""

__version__ = "2.0.0"
__author__ = "Google Antigravity & Tony"

from .core.categories import category_of, color_of, DEFAULT_CATEGORIES
from .core.scanner import scan, ScanResult, ScanProgress, human
from .core.organizer import organizar_pasta, OrganizeResult
from .core.undo import desfazer, encontrar_logs, encontrar_log_mais_recente, UndoResult

__all__ = [
    "__version__",
    "category_of",
    "color_of",
    "DEFAULT_CATEGORIES",
    "scan",
    "ScanResult",
    "ScanProgress",
    "human",
    "organizar_pasta",
    "OrganizeResult",
    "desfazer",
    "encontrar_logs",
    "encontrar_log_mais_recente",
    "UndoResult",
]
