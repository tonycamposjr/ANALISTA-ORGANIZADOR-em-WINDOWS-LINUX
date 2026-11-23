"""Janela principal da aplicação gráfica integrada (GUI)."""

import tkinter as tk
from tkinter import ttk

from .tab_analyst import TabAnalyst
from .tab_organizer import TabOrganizer
from .tab_settings import TabSettings
from .tab_undo import TabUndo


class App:
    """Aplicação Principal do Analista & Organizador de Arquivos."""

    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Analista & Organizador de Arquivos — Antigravity v2.0")
        root.geometry("840x660")
        root.minsize(740, 560)

        self._configure_styles()
        self._build_header()

        # Notebook com as 4 abas integradas
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        self.tab_analyst = TabAnalyst(self.notebook, app=self)
        self.tab_organizer = TabOrganizer(self.notebook, app=self)
        self.tab_undo = TabUndo(self.notebook, app=self)
        self.tab_settings = TabSettings(self.notebook, app=self)

        self.notebook.add(self.tab_analyst, text=" 📊 Analisador de Armazenamento ")
        self.notebook.add(self.tab_organizer, text=" 🗂️ Organizador de Arquivos ")
        self.notebook.add(self.tab_undo, text=" 🔄 Desfazer & Histórico ")
        self.notebook.add(self.tab_settings, text=" ⚙️ Categorias & Configurações ")

        # Rodapé com status unificado
        footer = ttk.Frame(self.root)
        footer.pack(fill="x", side="bottom", padx=10, pady=4)
        ttk.Label(
            footer,
            text="Analista & Organizador de Arquivos v2.0 · Antigravity Edition",
            font=("TkDefaultFont", 8),
            foreground="#666666"
        ).pack(side="left")

    def _configure_styles(self):
        try:
            style = ttk.Style(self.root)
            if "clam" in style.theme_names():
                style.theme_use("clam")

            style.configure("TNotebook.Tab", padding=[12, 6], font=("TkDefaultFont", 9, "bold"))
            style.configure("TButton", font=("TkDefaultFont", 9))
            style.configure("TLabelframe.Label", font=("TkDefaultFont", 9, "bold"), foreground="#1e3a8a")
        except Exception:
            pass

    def _build_header(self):
        hdr_frame = ttk.Frame(self.root)
        hdr_frame.pack(fill="x", padx=14, pady=(10, 6))

        title_lbl = ttk.Label(
            hdr_frame,
            text="Analista & Organizador de Arquivos",
            font=("TkDefaultFont", 15, "bold"),
            foreground="#1e3a8a"
        )
        title_lbl.pack(anchor="w")

        sub_lbl = ttk.Label(
            hdr_frame,
            text="Diagnóstico de capacidade, relatórios em PDF/CSV, organização inteligente e auditoria reversa.",
            font=("TkDefaultFont", 9),
            foreground="#555555"
        )
        sub_lbl.pack(anchor="w")

    def set_shared_path(self, path: str, source=None):
        """Sincroniza o caminho da pasta selecionada entre as abas ativas."""
        if not path:
            return
        if source != self.tab_analyst and hasattr(self, "tab_analyst"):
            self.tab_analyst.set_path(path)
        if source != self.tab_organizer and hasattr(self, "tab_organizer"):
            self.tab_organizer.set_path(path)
        if source != self.tab_undo and hasattr(self, "tab_undo"):
            self.tab_undo.set_path(path)

    def notify_undo_refresh(self):
        """Notifica a aba de Desfazer para atualizar a listagem de logs após uma organização."""
        if hasattr(self, "tab_undo"):
            self.tab_undo.refresh_logs()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
