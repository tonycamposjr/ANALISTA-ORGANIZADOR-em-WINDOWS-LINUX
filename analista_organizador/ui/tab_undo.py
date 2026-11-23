"""Aba 3: Desfazer e Histórico de Organizações (Rollback)."""

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import List, Optional

from .. import config
from ..core import undo
from .widgets import FolderPicker, LogBox, open_path_in_system


class TabUndo(ttk.Frame):
    """Aba responsável por auditar logs históricos de organização e reverter movimentos com total segurança."""

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.running = False
        self.found_logs: List[Path] = []
        self.selected_log_details: Optional[dict] = None

        cfg = config.load_config()
        self._build_ui(cfg)

    def _build_ui(self, cfg: dict):
        pad = {"padx": 14, "pady": 6}

        # 1. Seletor de pasta sincronizado
        self.picker = FolderPicker(
            self,
            label_text="Pasta onde foi realizada a organização:",
            default_value=cfg.get("last_path", ""),
            on_change=self._on_path_changed
        )
        self.picker.pack(fill="x", **pad)

        # 2. Painel de Seleção de Logs
        log_group = ttk.LabelFrame(self, text="Histórico de Logs Encontrados na Pasta")
        log_group.pack(fill="x", **pad)

        log_inner = ttk.Frame(log_group)
        log_inner.pack(fill="x", padx=10, pady=8)

        ttk.Label(log_inner, text="Arquivo de Log:").pack(side="left")
        self.log_combo_var = tk.StringVar()
        self.log_combo = ttk.Combobox(
            log_inner, textvariable=self.log_combo_var, state="readonly", width=42
        )
        self.log_combo.pack(side="left", padx=(6, 10))
        self.log_combo.bind("<<ComboboxSelected>>", self._on_log_selected)

        self.btn_refresh = ttk.Button(
            log_inner, text="🔄 Atualizar Logs", command=self.refresh_logs
        )
        self.btn_refresh.pack(side="left")

        # 3. Informações e Pré-visualização do Log Selecionado
        preview_group = ttk.LabelFrame(self, text="Detalhes das Operações do Log")
        preview_group.pack(fill="x", **pad)

        self.info_label = ttk.Label(
            preview_group,
            text="Nenhum log selecionado.",
            font=("TkDefaultFont", 9, "bold")
        )
        self.info_label.pack(anchor="w", padx=10, pady=(6, 2))

        # 4. Botões de Ação
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", **pad)

        self.btn_revert = ttk.Button(
            btn_frame,
            text="↩ Reverter Organização Deste Log",
            command=self._start_undo,
            state="disabled"
        )
        self.btn_revert.pack(side="left", padx=(0, 8))

        self.btn_open_folder = ttk.Button(
            btn_frame, text="📁 Abrir Pasta", command=self._open_folder
        )
        self.btn_open_folder.pack(side="left", padx=4)

        # 5. Barra de Progresso e Status
        self.progress = ttk.Progressbar(self, mode="determinate", maximum=100)
        self.progress.pack(fill="x", padx=14, pady=(6, 2))

        self.status_var = tk.StringVar(value="Selecione uma pasta para listar os logs de organização.")
        ttk.Label(self, textvariable=self.status_var, wraplength=760).pack(anchor="w", padx=14, pady=2)

        # 6. Caixa de Logs de Execução
        ttk.Label(self, text="Log de Reversão:").pack(anchor="w", padx=14, pady=(6, 2))
        self.log_box = LogBox(self, height=9)
        self.log_box.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        # Carga inicial dos logs
        self.refresh_logs()

    def _on_path_changed(self, new_path: str):
        self.app.set_shared_path(new_path, source=self)
        self.refresh_logs()

    def set_path(self, path: str):
        self.picker.set_path(path)
        self.refresh_logs()

    def _open_folder(self):
        path = self.picker.get_path().strip()
        if path and os.path.isdir(path):
            open_path_in_system(path)

    def refresh_logs(self):
        path = self.picker.get_path().strip()
        if not path or not os.path.isdir(path):
            self.log_combo["values"] = []
            self.log_combo_var.set("")
            self.btn_revert.configure(state="disabled")
            self.info_label.configure(text="Pasta inválida ou não selecionada.")
            return

        self.found_logs = undo.encontrar_logs(path)
        if not self.found_logs:
            self.log_combo["values"] = ["Nenhum log encontrado nesta pasta"]
            self.log_combo_var.set("Nenhum log encontrado nesta pasta")
            self.btn_revert.configure(state="disabled")
            self.info_label.configure(text="Nenhum registro _organizacao_log_*.json foi localizado nesta pasta.")
            return

        display_list = [f"{p.name} ({len(undo.ler_detalhes_log(p).get('operacoes', []))} itens)" for p in self.found_logs]
        self.log_combo["values"] = display_list
        self.log_combo.current(0)
        self._on_log_selected()

    def _on_log_selected(self, _event=None):
        idx = self.log_combo.current()
        if idx < 0 or idx >= len(self.found_logs):
            return

        log_path = self.found_logs[idx]
        details = undo.ler_detalhes_log(log_path)
        self.selected_log_details = details

        if details.get("valido"):
            total = details.get("total_operacoes", 0)
            self.info_label.configure(
                text=f"Log Selecionado: {log_path.name}  |  Total de arquivos/pastas movidos: {total}"
            )
            self.btn_revert.configure(state="normal")
            self.status_var.set(f"Pronto para reverter {total} item(ns). Clique no botão abaixo.")
        else:
            self.info_label.configure(text=f"Log inválido: {details.get('erro')}")
            self.btn_revert.configure(state="disabled")

    def _start_undo(self):
        if self.running or not self.selected_log_details:
            return

        idx = self.log_combo.current()
        if idx < 0 or idx >= len(self.found_logs):
            return

        log_path = self.found_logs[idx]
        total = self.selected_log_details.get("total_operacoes", 0)

        msg = (
            f"Atenção: Você irá desfazer a organização gravada em:\n  {log_path.name}\n\n"
            f"Isso moverá de volta {total} item(ns) para os seus locais de origem.\n\n"
            f"Deseja realmente prosseguir com a reversão?"
        )
        if not messagebox.askyesno("Confirmar Reversão (Undo)", msg, icon="warning"):
            return

        self.running = True
        self.btn_revert.configure(state="disabled")
        self.btn_refresh.configure(state="disabled")
        self.progress["value"] = 0
        self.log_box.clear()

        thread = threading.Thread(
            target=self._worker,
            args=(log_path,),
            daemon=True
        )
        thread.start()

    def _worker(self, log_path: Path):
        try:
            def on_prog(atual: int, total: int, item_name: str, status: str):
                frac = atual / total if total else 1.0
                self.after(0, lambda: self._update_progress(frac, atual, total, item_name))

            def on_l(msg: str):
                self.after(0, lambda: self.log_box.log(msg))

            res = undo.desfazer(
                caminho_log=log_path,
                on_progress=on_prog,
                on_log=on_l
            )

            self.after(0, lambda: self._on_finish(res))

        except Exception as e:
            err = str(e)
            self.after(0, lambda: self._on_error(err))

    def _update_progress(self, frac: float, atual: int, total: int, item_name: str):
        self.progress["value"] = frac * 100
        self.status_var.set(f"Revertendo [{atual}/{total}]: {item_name}")

    def _on_finish(self, res: undo.UndoResult):
        self.progress["value"] = 100
        self.running = False
        self.btn_revert.configure(state="normal")
        self.btn_refresh.configure(state="normal")
        self.status_var.set(f"Reversão finalizada: {res.revertidos} de {res.total} itens restaurados.")

        msg = f"Reversão concluída com sucesso!\n\nItens restaurados ao local original: {res.revertidos} de {res.total}."
        if res.erros:
            msg += f"\n\nObservação: Houve {len(res.erros)} aviso(s) ou exceção(ões). Verifique o log detalhado."
        messagebox.showinfo("Reversão Concluída", msg)

        # Atualizar lista de logs
        self.refresh_logs()

    def _on_error(self, err: str):
        self.progress["value"] = 0
        self.running = False
        self.btn_revert.configure(state="normal")
        self.btn_refresh.configure(state="normal")
        self.status_var.set(f"Erro na reversão: {err}")
        self.log_box.log(f"ERRO: {err}")
        messagebox.showerror("Erro ao Desfazer", f"Falha na execução:\n{err}")
