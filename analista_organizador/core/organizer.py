"""Módulo de organização estruturada de pastas e arquivos."""

import hashlib
import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .categories import DEFAULT_CATEGORIES, category_of

PASTA_OUTRAS_PASTAS = "Pastas"
PASTA_OUTROS = "Outros"
PASTA_DUPLICADOS = "Duplicados"
ARQUIVOS_IGNORADOS = {".ds_store", "thumbs.db", "desktop.ini"}
PREFIXO_LOG = "_organizacao_log_"


@dataclass
class OrganizeResult:
    total: int = 0
    movidos: int = 0
    duplicados: int = 0
    erros: List[str] = field(default_factory=list)
    log_file: Optional[Path] = None
    operacoes: List[Dict[str, str]] = field(default_factory=list)
    dry_run: bool = False


def eh_arquivo_ignorado(nome: str) -> bool:
    """Arquivos ocultos e de sistema não devem ser movidos."""
    if nome.startswith("."):
        return True
    if nome.lower() in ARQUIVOS_IGNORADOS:
        return True
    return False


def destino_sem_conflito(pasta_destino: Path, nome: str) -> Path:
    """Gera um caminho único no destino caso já exista arquivo com o mesmo nome."""
    destino = pasta_destino / nome
    if not destino.exists():
        return destino

    base = Path(nome).stem
    extensao = Path(nome).suffix
    contador = 1
    while destino.exists():
        novo_nome = f"{base} ({contador}){extensao}"
        destino = pasta_destino / novo_nome
        contador += 1
    return destino


def calcular_hash(caminho: Path, bloco: int = 65536) -> str:
    """Calcula hash SHA-256 do arquivo para detecção segura de duplicatas."""
    h = hashlib.sha256()
    try:
        with open(caminho, "rb") as f:
            while True:
                dados = f.read(bloco)
                if not dados:
                    break
                h.update(dados)
        return h.hexdigest()
    except (OSError, PermissionError):
        return ""


def subpasta_por_data(item: Path) -> str:
    """Retorna subpasta 'Ano/Mês' baseada na data de modificação."""
    try:
        data = datetime.fromtimestamp(item.stat().st_mtime)
        return f"{data.year}/{data.month:02d}"
    except OSError:
        return ""


def organizar_pasta(
    caminho_pasta: str | Path,
    categorias: Optional[Dict[str, List[str]]] = None,
    dry_run: bool = False,
    por_data: bool = False,
    detectar_duplicados: bool = False,
    on_progress: Optional[Callable[[int, int, str, str], None]] = None,
    on_log: Optional[Callable[[str], None]] = None,
) -> OrganizeResult:
    """Organiza o conteúdo de uma pasta em categorias temáticas.

    Parâmetros:
        caminho_pasta: Diretório a ser organizado.
        categorias: Mapeamento de categorias e extensões (usa DEFAULT_CATEGORIES se None).
        dry_run: Se True, apenas simula as movimentações sem alterar nada no disco.
        por_data: Se True, cria subpastas Ano/Mês dentro de cada categoria.
        detectar_duplicados: Se True, detecta cópias por hash e move para 'Duplicados/'.
        on_progress: Callback opcional (atual, total, nome_item, status).
        on_log: Callback opcional para mensagens de log em tempo real.
    """
    def log(msg: str):
        if on_log:
            on_log(msg)

    pasta = Path(caminho_pasta).resolve()
    if not pasta.is_dir():
        res = OrganizeResult(dry_run=dry_run)
        res.erros.append(f"Diretório inexistente ou inacessível: {pasta}")
        return res

    cat_map = categorias if categorias is not None else DEFAULT_CATEGORIES
    nomes_conhecidos = set(cat_map.keys()) | {PASTA_OUTRAS_PASTAS, PASTA_OUTROS, PASTA_DUPLICADOS}

    try:
        itens = sorted(pasta.iterdir(), key=lambda p: p.name.lower())
    except (OSError, PermissionError) as e:
        res = OrganizeResult(dry_run=dry_run)
        res.erros.append(f"Erro ao listar pasta {pasta}: {e}")
        return res

    itens_validos = [
        i for i in itens
        if not i.name.startswith(PREFIXO_LOG) and not eh_arquivo_ignorado(i.name)
    ]

    res = OrganizeResult(total=len(itens_validos), dry_run=dry_run)

    if not itens_validos:
        log("A pasta selecionada está vazia (ou só possui arquivos ocultos/ignorados).")
        return res

    hashes_vistos: Dict[str, str] = {}
    log_operacoes = []

    log(f"{'[SIMULAÇÃO] ' if dry_run else ''}Processando {res.total} item(ns) em: {pasta}")

    for indice, item in enumerate(itens_validos, start=1):
        if item.is_dir() and item.name in nomes_conhecidos:
            if on_progress:
                on_progress(indice, res.total, item.name, "Ignorado (pasta de categoria)")
            continue

        try:
            if item.is_dir():
                categoria = PASTA_OUTRAS_PASTAS
            elif detectar_duplicados:
                hash_item = calcular_hash(item)
                if hash_item and hash_item in hashes_vistos:
                    categoria = PASTA_DUPLICADOS
                    res.duplicados += 1
                else:
                    if hash_item:
                        hashes_vistos[hash_item] = item.name
                    categoria = category_of(item.suffix, categories=cat_map)
            else:
                categoria = category_of(item.suffix, categories=cat_map)

            pasta_categoria = pasta / categoria

            if por_data and categoria not in (PASTA_OUTRAS_PASTAS, PASTA_DUPLICADOS):
                sub = subpasta_por_data(item)
                if sub:
                    pasta_categoria = pasta_categoria / sub

            destino = destino_sem_conflito(pasta_categoria, item.name)

            if dry_run:
                msg = f"Moveria: {item.name} -> {destino.relative_to(pasta)}"
                log(f"[{indice}/{res.total}] {msg}")
            else:
                pasta_categoria.mkdir(parents=True, exist_ok=True)
                shutil.move(str(item), str(destino))
                msg = f"Movido: {item.name} -> {destino.relative_to(pasta)}"
                log(f"[{indice}/{res.total}] {msg}")
                log_operacoes.append({
                    "origem": str(item),
                    "destino": str(destino),
                    "data": datetime.now().isoformat(),
                    "tipo": "diretório" if item.is_dir() else "arquivo"
                })

            res.movidos += 1
            if on_progress:
                on_progress(indice, res.total, item.name, "OK")

        except (OSError, PermissionError, shutil.Error) as e:
            err_msg = f"{item.name}: {e}"
            res.erros.append(err_msg)
            log(f"[{indice}/{res.total}] ERRO ao mover {item.name}: {e}")
            if on_progress:
                on_progress(indice, res.total, item.name, f"ERRO: {e}")

    res.operacoes = log_operacoes

    if not dry_run and log_operacoes:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        caminho_log = pasta / f"{PREFIXO_LOG}{timestamp}.json"
        try:
            with open(caminho_log, "w", encoding="utf-8") as f:
                json.dump(log_operacoes, f, ensure_ascii=False, indent=2)
            res.log_file = caminho_log
            log(f"\nLog de auditoria gerado: {caminho_log.name}")
            log("Use a aba ou comando 'Desfazer' nesta pasta para reverter caso necessário.")
        except OSError as e:
            res.erros.append(f"Não foi possível salvar log em {caminho_log}: {e}")
            log(f"ERRO ao salvar log: {e}")

    log(
        f"\n{'Simulação concluída' if dry_run else 'Organização concluída'}! "
        f"{res.movidos} item(ns) {'seriam movidos' if dry_run else 'movidos com sucesso'}."
    )
    if detectar_duplicados and res.duplicados:
        log(f"Duplicados isolados em '{PASTA_DUPLICADOS}/': {res.duplicados}")
    if res.erros:
        log(f"Avisos / erros encontrados: {len(res.erros)}")

    return res
