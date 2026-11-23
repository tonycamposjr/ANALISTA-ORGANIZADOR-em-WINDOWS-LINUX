"""Componentes visuais reutilizáveis para a interface gráfica Tkinter."""

import os
import subprocess
import sys
import webbrowser
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Callable, Optional


def open_path_in_system(path: str) -> bool:
    """Abre um arquivo ou pasta no gerenciador de arquivos/aplicativo padrão do sistema."""
    if not path or not os.path.exists(path):
        return False

    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # noqa: S606
            return True
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
            return True
        else:
            subprocess.Popen(["xdg-open", path])
            return True
    except Exception:
        try:
            webbrowser.open("file://" + os.path.abspath(path).replace("\\", "/"))
            return True
        except Exception:
            return False


class FolderPicker(ttk.Frame):
    """Componente unificado para seleção de pasta com campo de texto e botão Procurar."""

    def __init__(self, parent, label_text: str = "Pasta / unidade:", default_value: str = "", on_change: Optional[Callable[[str], None]] = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_change = on_change
        self.path_var = tk.StringVar(value=default_value)
        if on_change:
            self.path_var.trace_add("write", lambda *_: on_change(self.path_var.get()))

        ttk.Label(self, text=label_text).pack(anchor="w", pady=(0, 2))
        row = ttk.Frame(self)
        row.pack(fill="x", expand=True)

        self.entry = ttk.Entry(row, textvariable=self.path_var)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn = ttk.Button(row, text="Procurar...", command=self._browse)
        self.btn.pack(side="right")

    def _browse(self):
        initial = self.path_var.get().strip() or os.path.expanduser("~")
        if not os.path.isdir(initial):
            initial = os.path.expanduser("~")
        chosen = filedialog.askdirectory(title="Selecione a pasta", initialdir=initial)
        if chosen:
            self.path_var.set(chosen)

    def get_path(self) -> str:
        return self.path_var.get().strip()

    def set_path(self, path: str):
        self.path_var.set(path)


class LogBox(ttk.Frame):
    """Caixa de texto estilizada para exibição de logs e histórico com scrollbar."""

    def __init__(self, parent, height: int = 10, **kwargs):
        super().__init__(parent, **kwargs)
        self.text = tk.Text(
            self,
            height=height,
            wrap="word",
            state="disabled",
            font=("TkFixedFont", 9),
            bg="#fdfdfd",
            fg="#222222",
            relief="solid",
            borderwidth=1,
        )
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)

        # Configurar tags visuais de cor
        self.text.tag_configure("INFO", foreground="#1e3a8a")
        self.text.tag_configure("SUCCESS", foreground="#15803d")
        self.text.tag_configure("WARNING", foreground="#b45309")
        self.text.tag_configure("ERROR", foreground="#b91c1c")
        self.text.tag_configure("SIMULATION", foreground="#6d28d9")

    def log(self, message: str):
        self.text.configure(state="normal")
        tag = None
        upper = message.upper()
        if "ERRO" in upper or "FALHA" in upper:
            tag = "ERROR"
        elif "CONCLUÍD" in upper or "CONCLUID" in upper or "SUCESSO" in upper or "OK" in upper:
            tag = "SUCCESS"
        elif "AVISO" in upper or "ATENÇÃO" in upper or "ALERTA" in upper:
            tag = "WARNING"
        elif "[SIMULAÇÃO]" in message or "SIMUL" in upper:
            tag = "SIMULATION"

        if tag:
            self.text.insert("end", message + "\n", tag)
        else:
            self.text.insert("end", message + "\n")
        self.text.see("end")
        self.text.configure(state="disabled")

    def clear(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")
