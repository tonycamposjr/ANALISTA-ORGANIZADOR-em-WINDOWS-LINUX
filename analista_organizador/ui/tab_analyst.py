"""Aba 1: Analisador de Armazenamento e Gerador de Relatórios (Disk Index)."""

import os
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from .. import config
from ..core import scanner
from ..core.scanner import ScanProgress
from ..reports.csv_exporter import write_csv
from ..reports.disk_report import build as build_pdf_report
from .widgets import FolderPicker, LogBox, open_path_in_system


class TabAnalyst(ttk.Frame):
    """Aba responsável pela auditoria de armazenamento, mapeamento de duplicatas e relatórios PDF/CSV."""

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.scanning = False
        self.last_pdf = None
        self.last_path = None

        cfg = config.load_config()
        self._build_ui(cfg)

    def _build_ui(self, cfg: dict):
        pad = {"padx": 14, "pady": 6}

        # 1. Seletor de pasta sincronizado
        self.picker = FolderPicker(
            self,
            label_text="Pasta ou Unidade para analisar:",
            default_value=cfg.get("last_path", ""),
            on_change=self._on_path_changed
        )
        self.picker.pack(fill="x", **pad)

        # 2. Painel de Opções de Análise
        opt_group = ttk.LabelFrame(self, text="Opções da Varredura e Relatórios")
        opt_group.pack(fill="x", **pad)

        opt_inner = ttk.Frame(opt_group)
        opt_inner.pack(fill="x", padx=10, pady=8)

        ttk.Label(opt_inner, text="Detecção de Duplicados:").pack(side="left")
        self.dup_var = tk.StringVar(value=cfg.get("dup_mode", "rapido"))
        self.dup_combo = ttk.Combobox(
            opt_inner, textvariable=self.dup_var, state="readonly",
            width=10, values=["off", "rapido", "parcial", "completo"]
        )
        self.dup_combo.pack(side="left", padx=(4, 16))

        ttk.Label(opt_inner, text="Arquivos Maiores que (MB):").pack(side="left")
        self.threshold_var = tk.StringVar(value=str(cfg.get("threshold_mb", 50)))
        self.threshold_spin = ttk.Spinbox(
            opt_inner, from_=1, to=100000, width=7, textvariable=self.threshold_var
        )
        self.threshold_spin.pack(side="left", padx=(4, 16))

        self.csv_var = tk.BooleanVar(value=cfg.get("csv_export", True))
        self.csv_check = ttk.Checkbutton(
            opt_inner, text="Exportar Inventário CSV", variable=self.csv_var
        )
        self.csv_check.pack(side="left")

        # 3. Botões de Ação
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", **pad)

        self.btn_start = ttk.Button(
            btn_frame, text="▶ Analisar e Gerar Relatórios", command=self.start_analysis
        )
        self.btn_start.pack(side="left", padx=(0, 8))

        self.btn_open_pdf = ttk.Button(
            btn_frame, text="📄 Abrir PDF Gerado", command=self._open_pdf, state="disabled"
        )
        self.btn_open_pdf.pack(side="left", padx=4)

        self.btn_open_folder = ttk.Button(
            btn_frame, text="📁 Abrir Pasta Analisada", command=self._open_folder
        )
        self.btn_open_folder.pack(side="left", padx=4)

        # 4. Progresso e Status
        self.progress = ttk.Progressbar(self, mode="determinate", maximum=100)
        self.progress.pack(fill="x", padx=14, pady=(6, 2))

        self.status_var = tk.StringVar(value="Pronto para analisar. Escolha a pasta e clique no botão.")
        ttk.Label(self, textvariable=self.status_var, wraplength=760).pack(anchor="w", padx=14, pady=2)

        # 5. Caixa de Logs
        ttk.Label(self, text="Log de Execução:").pack(anchor="w", padx=14, pady=(6, 2))
        self.log_box = LogBox(self, height=9)
        self.log_box.pack(fill="both", expand=True, padx=14, pady=(0, 14))

    def _on_path_changed(self, new_path: str):
        self.app.set_shared_path(new_path, source=self)

    def set_path(self, path: str):
        self.picker.set_path(path)

    def start_analysis(self):
        if self.scanning:
            return

        path = self.picker.get_path().strip()
        if not path or not os.path.isdir(path):
            messagebox.showerror("Caminho Inválido", "Por favor selecione uma pasta ou unidade válida.")
            return

        try:
            threshold_mb = max(1, int(self.threshold_var.get()))
            threshold_bytes = threshold_mb * 1024 * 1024
        except ValueError:
            threshold_bytes = 50 * 1024 * 1024
            threshold_mb = 50

        dup_mode = self.dup_var.get() or "rapido"
        want_csv = self.csv_var.get()

        config.save_config({
            "last_path": path,
            "threshold_mb": threshold_mb,
            "dup_mode": dup_mode,
            "csv_export": want_csv
        })

        base_name = os.path.basename(path.rstrip("/\\")) or "volume"
        out_pdf = os.path.join(os.path.expanduser("~"), f"indice_{base_name}.pdf")
        out_csv = os.path.join(os.path.expanduser("~"), f"indice_{base_name}.csv")

        self.scanning = True
        self.last_path = path
        self.btn_start.configure(state="disabled")
        self.btn_open_pdf.configure(state="disabled")
        self.progress["value"] = 0
        self.log_box.clear()
        self.log_box.log(f"Iniciando varredura analítica em: {path}")

        thread = threading.Thread(
            target=self._worker,
            args=(path, threshold_bytes, dup_mode, want_csv, out_pdf, out_csv),
            daemon=True
        )
        thread.start()

    def _progress_callback(self, files: int, size: int, frac: float, eta: str):
        def update():
            self.progress["value"] = frac * 100
            pct_txt = "{:.0f}%".format(frac * 100)
            self.status_var.set(
                f"Analisando... {files:,} arquivos · {scanner.human(size)} · {pct_txt} {eta}"
            )
        self.after(0, update)

    def _csv_progress(self, n: int):
        self.after(0, lambda: self.status_var.set(f"Exportando inventário CSV... {n:,} arquivos processados"))

    def _worker(self, path: str, threshold: int, dup_mode: str, want_csv: bool, out_pdf: str, out_csv: str):
        try:
            progress = ScanProgress(callback=self._progress_callback, root=path)
            result = scanner.scan(path, progress=progress, big_threshold=threshold, dup_mode=dup_mode)

            self.after(0, lambda: self.log_box.log(
                f"Varredura concluída: {result.total_files:,} arquivos · {scanner.human(result.total_size)} · {result.total_dirs:,} pastas"
            ))

            if result.dup_totals[1]:
                self.after(0, lambda: self.log_box.log(
                    f"Duplicados identificados ({dup_mode}): {result.dup_totals[1]} grupos com {scanner.human(result.dup_totals[0])} desperdiçados"
                ))

            self.after(0, lambda: self.status_var.set("Construindo relatório PDF vetorial..."))
            build_pdf_report(result, out_pdf)
            self.last_pdf = out_pdf
            self.after(0, lambda: self.log_box.log(f"Relatório PDF salvo em: {out_pdf}"))

            if want_csv:
                self.after(0, lambda: self.status_var.set("Gerando arquivo de inventário CSV..."))
                total_csv = write_csv(result, out_csv, progress=self._csv_progress)
                self.after(0, lambda: self.log_box.log(f"Inventário CSV salvo em: {out_csv} ({total_csv:,} linhas)"))

            self.after(0, lambda: self._on_success(out_pdf))

        except Exception as e:
            err = str(e)
            self.after(0, lambda: self._on_failure(err))

    def _on_success(self, pdf_path: str):
        self.progress["value"] = 100
        self.scanning = False
        self.btn_start.configure(state="normal")
        self.btn_open_pdf.configure(state="normal")
        self.status_var.set(f"Concluído com sucesso! PDF disponível em: {pdf_path}")
        self.log_box.log("Processo concluído com êxito!")

        if messagebox.askyesno("Análise Concluída", f"Relatório PDF gerado com sucesso!\n{pdf_path}\n\nDeseja abrir o documento agora?"):
            open_path_in_system(pdf_path)

    def _on_failure(self, error_msg: str):
        self.progress["value"] = 0
        self.scanning = False
        self.btn_start.configure(state="normal")
        self.status_var.set(f"Erro durante a análise: {error_msg}")
        self.log_box.log(f"ERRO: {error_msg}")
        messagebox.showerror("Falha na Análise", f"Ocorreu um erro durante a execução:\n{error_msg}")

    def _open_pdf(self):
        if self.last_pdf:
            open_path_in_system(self.last_pdf)

    def _open_folder(self):
        path = self.picker.get_path().strip()
        if path and os.path.isdir(path):
            open_path_in_system(path)
