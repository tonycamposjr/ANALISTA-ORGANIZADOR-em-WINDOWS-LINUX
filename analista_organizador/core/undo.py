"""Módulo de auditoria reversa (Rollback) para desfazer organizações."""

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

PREFIXO_LOG = "_organizacao_log_"


@dataclass
class UndoResult:
    revertidos: int = 0
    total: int = 0
    erros: List[str] = field(default_factory=list)
    log_file: Optional[Path] = None


def encontrar_logs(pasta: Path | str) -> List[Path]:
    """Retorna lista de arquivos de log de organização na pasta, ordenados por data decrescente."""
    p = Path(pasta).resolve()
    if not p.is_dir():
        return []
    logs = sorted(p.glob(f"{PREFIXO_LOG}*.json"), reverse=True)
    return logs


def encontrar_log_mais_recente(pasta: Path | str) -> Optional[Path]:
    """Localiza o arquivo de log mais recente na pasta especificada."""
    logs = encontrar_logs(pasta)
    return logs[0] if logs else None


def ler_detalhes_log(caminho_log: Path | str) -> Dict[str, Any]:
    """Lê o arquivo de log e retorna metadados e preview das operações."""
    p = Path(caminho_log)
    if not p.is_file():
        return {"valido": False, "erro": "Arquivo de log não encontrado"}

    try:
        with open(p, "r", encoding="utf-8") as f:
            operacoes = json.load(f)
        if not isinstance(operacoes, list):
            return {"valido": False, "erro": "Formato de log inválido"}

        return {
            "valido": True,
            "arquivo": p.name,
            "caminho": str(p),
            "total_operacoes": len(operacoes),
            "primeiras_operacoes": operacoes[:10],
            "operacoes": operacoes
        }
    except (OSError, json.JSONDecodeError) as e:
        return {"valido": False, "erro": str(e)}


def desfazer(
    caminho_log: Path | str,
    on_progress: Optional[Callable[[int, int, str, str], None]] = None,
    on_log: Optional[Callable[[str], None]] = None,
) -> UndoResult:
    """Executa a reversão completa das operações registradas no arquivo de log.

    Processa em ordem estritamente reversa (LIFO) e previne sobreposição acidental.
    """
    def log(msg: str):
        if on_log:
            on_log(msg)

    p_log = Path(caminho_log).resolve()
    res = UndoResult(log_file=p_log)

    if not p_log.is_file():
        res.erros.append(f"Arquivo de log não encontrado: {p_log}")
        log(f"ERRO: Arquivo de log inexistente: {p_log}")
        return res

    try:
        with open(p_log, "r", encoding="utf-8") as f:
            operacoes = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        res.erros.append(f"Erro ao carregar log: {e}")
        log(f"ERRO: Não foi possível ler o log: {e}")
        return res

    if not isinstance(operacoes, list):
        res.erros.append("Conteúdo do log não é uma lista de operações válida.")
        return res

    res.total = len(operacoes)
    log(f"Iniciando reversão de {res.total} item(ns) a partir de: {p_log.name}")

    # Processar na ordem inversa à que foi executada
    for indice, op in enumerate(reversed(operacoes), start=1):
        origem = Path(op["destino"])           # onde o item está atualmente
        destino_original = Path(op["origem"])  # onde ele estava originalmente

        try:
            if not origem.exists():
                err = f"{origem.name}: não encontrado no local atual (pode ter sido renomeado ou movido manualmente)"
                res.erros.append(err)
                log(f"[{indice}/{res.total}] AVISO: {err}")
                if on_progress:
                    on_progress(indice, res.total, origem.name, "Não encontrado")
                continue

            # Garantir existência da pasta original
            destino_original.parent.mkdir(parents=True, exist_ok=True)

            # Prevenir sobrescrita caso já exista algo no local original
            destino_final = destino_original
            if destino_final.exists():
                base = destino_final.stem
                extensao = destino_final.suffix
                contador = 1
                while destino_final.exists():
                    destino_final = destino_original.parent / f"{base} (restaurado {contador}){extensao}"
                    contador += 1

            shutil.move(str(origem), str(destino_final))
            res.revertidos += 1
            log(f"[{indice}/{res.total}] Restaurado: {origem.name} -> {destino_final}")
            if on_progress:
                on_progress(indice, res.total, origem.name, "Restaurado")

        except (OSError, shutil.Error) as e:
            err = f"{origem.name}: {e}"
            res.erros.append(err)
            log(f"[{indice}/{res.total}] ERRO ao restaurar {origem.name}: {e}")
            if on_progress:
                on_progress(indice, res.total, origem.name, f"ERRO: {e}")

    log(f"\nProcesso concluído: {res.revertidos} de {res.total} item(ns) restaurados com sucesso.")
    if res.erros:
        log(f"{len(res.erros)} problema(s) encontrado(s) durante a reversão.")

    return res
