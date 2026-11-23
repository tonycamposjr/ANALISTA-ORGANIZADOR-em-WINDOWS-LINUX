"""Aba 2: Organizador de Arquivos e Pastas em Categorias."""

import os
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from .. import config
from ..core import organizer
from ..core.categories import carregar_categorias
from .widgets import FolderPicker, LogBox, open_path_in_system


class TabOrganizer(ttk.Frame):
    """Aba responsável pela organização física de arquivos e subpastas em categorias temáticas."""

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.running = False

        cfg = config.load_config()
        self._build_ui(cfg)

    def _build_ui(self, cfg: dict):
        pad = {"padx": 14, "pady": 6}

        # 1. Seletor de pasta sincronizado
        self.picker = FolderPicker(
            self,
            label_text="Pasta a ser organizada:",
            default_value=cfg.get("last_path", ""),
            on_change=self._on_path_changed
        )
        self.picker.pack(fill="x", **pad)

        # 2. Painel de Regras e Opções
        opt_group = ttk.LabelFrame(self, text="Opções e Parâmetros de Organização")
        opt_group.pack(fill="x", **pad)

        opt_inner = ttk.Frame(opt_group)
        opt_inner.pack(fill="x", padx=10, pady=8)

        self.dry_run_var = tk.BooleanVar(value=cfg.get("organize_dry_run", True))
        self.chk_dry = ttk.Checkbutton(
            opt_inner,
            text="Modo Simulação (Dry-Run) — Apenas preview, sem mover nada",
            variable=self.dry_run_var
        )
        self.chk_dry.pack(anchor="w", pady=2)

        self.por_data_var = tk.BooleanVar(value=cfg.get("organize_por_data", False))
        self.chk_data = ttk.Checkbutton(
            opt_inner,
            text="Organização Temporal — Criar subpastas Ano/Mês dentro de cada categoria",
            variable=self.por_data_var
        )
        self.chk_data.pack(anchor="w", pady=2)

        self.duplicados_var = tk.BooleanVar(value=cfg.get("organize_duplicados", False))
        self.chk_dup = ttk.Checkbutton(
            opt_inner,
            text="Isolar Duplicados — Calcular hash e mover réplicas para a pasta 'Duplicados/'",
            variable=self.duplicados_var
        )
        self.chk_dup.pack(anchor="w", pady=2)

        # 3. Botões de Ação
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", **pad)

        self.btn_run = ttk.Button(
            btn_frame, text="⚡ Iniciar Organização", command=self._start_organize
        )
        self.btn_run.pack(side="left", padx=(0, 8))

        self.btn_dry = ttk.Button(
            btn_frame, text="🔍 Simular Primeiro (Recomendado)", command=self._start_dry_run
        )
        self.btn_dry.pack(side="left", padx=4)

        self.btn_open_folder = ttk.Button(
            btn_frame, text="📁 Abrir Pasta", command=self._open_folder
        )
        self.btn_open_folder.pack(side="left", padx=4)

        # 4. Barra de Progresso e Status
        self.progress = ttk.Progressbar(self, mode="determinate", maximum=100)
        self.progress.pack(fill="x", padx=14, pady=(6, 2))

        self.status_var = tk.StringVar(
            value="Selecione a pasta, ajuste as regras desejadas e clique em Simular ou Organizar."
        )
        ttk.Label(self, textvariable=self.status_var, wraplength=760).pack(anchor="w", padx=14, pady=2)

        # 5. Caixa de Logs
        ttk.Label(self, text="Log de Operações:").pack(anchor="w", padx=14, pady=(6, 2))
        self.log_box = LogBox(self, height=9)
        self.log_box.pack(fill="both", expand=True, padx=14, pady=(0, 14))

    def _on_path_changed(self, new_path: str):
        self.app.set_shared_path(new_path, source=self)

    def set_path(self, path: str):
        self.picker.set_path(path)

    def _open_folder(self):
        path = self.picker.get_path().strip()
        if path and os.path.isdir(path):
            open_path_in_system(path)

    def _start_dry_run(self):
        self.dry_run_var.set(True)
        self._start_organize()

    def _start_organize(self):
        if self.running:
            return

        path = self.picker.get_path().strip()
        if not path or not os.path.isdir(path):
            messagebox.showerror("Caminho Inválido", "Por favor selecione uma pasta válida para organizar.")
            return

        is_dry = self.dry_run_var.get()
        por_data = self.por_data_var.get()
        duplicados = self.duplicados_var.get()

        # Confirmação caso não seja simulação
        if not is_dry:
            msg = (
                f"Você está prestes a mover arquivos e subpastas em:\n  {path}\n\n"
                f"Opções selecionadas:\n"
                f" - Por data (Ano/Mês): {'Sim' if por_data else 'Não'}\n"
                f" - Isolar duplicados: {'Sim' if duplicados else 'Não'}\n\n"
                f"Será gerado um log de reversão permitindo desfazer tudo depois.\n"
                f"Deseja prosseguir com a organização física?"
            )
            if not messagebox.askyesno("Confirmar Organização", msg, icon="warning"):
                return

        # Salvar preferências
        config.save_config({
            "last_path": path,
            "organize_dry_run": is_dry,
            "organize_por_data": por_data,
            "organize_duplicados": duplicados,
        })

        self.running = True
        self.btn_run.configure(state="disabled")
        self.btn_dry.configure(state="disabled")
        self.progress["value"] = 0
        self.log_box.clear()

        thread = threading.Thread(
            target=self._worker,
            args=(path, is_dry, por_data, duplicados),
            daemon=True
        )
        thread.start()

    def _worker(self, path: str, dry_run: bool, por_data: bool, duplicados: bool):
        try:
            categorias = carregar_categorias()

            def on_prog(atual: int, total: int, item_name: str, status: str):
                frac = atual / total if total else 1.0
                self.after(0, lambda: self._update_progress(frac, atual, total, item_name))

            def on_l(msg: str):
                self.after(0, lambda: self.log_box.log(msg))

            res = organizer.organizar_pasta(
                caminho_pasta=path,
                categorias=categorias,
                dry_run=dry_run,
                por_data=por_data,
                detectar_duplicados=duplicados,
                on_progress=on_prog,
                on_log=on_l
            )

            self.after(0, lambda: self._on_finish(res, dry_run))

        except Exception as e:
            err = str(e)
            self.after(0, lambda: self._on_error(err))

    def _update_progress(self, frac: float, atual: int, total: int, item_name: str):
        self.progress["value"] = frac * 100
        self.status_var.set(f"Processando [{atual}/{total}]: {item_name}")

    def _on_finish(self, res: organizer.OrganizeResult, dry_run: bool):
        self.progress["value"] = 100
        self.running = False
        self.btn_run.configure(state="normal")
        self.btn_dry.configure(state="normal")

        if dry_run:
            self.status_var.set(f"Simulação concluída! {res.movidos} item(ns) seriam organizados.")
            messagebox.showinfo(
                "Simulação Concluída",
                f"Modo Simulação (Dry-Run) concluído!\n\n"
                f"Total de itens avaliados: {res.total}\n"
                f"Itens que seriam movidos: {res.movidos}\n"
                f"Duplicados identificados: {res.duplicados}\n\n"
                f"Nenhum arquivo foi alterado no disco."
            )
        else:
            self.status_var.set(f"Organização concluída! {res.movidos} item(ns) movidos com sucesso.")
            # Notificar aba Undo para atualizar lista de logs
            self.app.notify_undo_refresh()

            msg = (
                f"Organização concluída com sucesso!\n\n"
                f"Itens organizados: {res.movidos}\n"
                f"Duplicados isolados: {res.duplicados}\n"
            )
            if res.log_file:
                msg += f"\nLog de auditoria gerado:\n{res.log_file.name}\n(Você pode desfazer a qualquer momento na aba Desfazer)."
            messagebox.showinfo("Sucesso", msg)

    def _on_error(self, err: str):
        self.progress["value"] = 0
        self.running = False
        self.btn_run.configure(state="normal")
        self.btn_dry.configure(state="normal")
        self.status_var.set(f"Erro: {err}")
        self.log_box.log(f"ERRO: {err}")
        messagebox.showerror("Erro na Organização", f"Ocorreu um problema:\n{err}")
