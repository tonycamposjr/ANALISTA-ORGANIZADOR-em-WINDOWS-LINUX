"""Aba 4: Visualização e Configuração de Categorias e Extensões."""

import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List

from ..core import categories
from ..core.categories import DEFAULT_CATEGORIES, carregar_categorias, salvar_categorias


class TabSettings(ttk.Frame):
    """Aba responsável pela visualização de categorias, extensões associadas e personalização."""

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.current_categories: Dict[str, List[str]] = carregar_categorias()
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 14, "pady": 6}

        # 1. Cabeçalho Explicativo
        hdr = ttk.Label(
            self,
            text="Regras de Categorização de Arquivos",
            font=("TkDefaultFont", 11, "bold")
        )
        hdr.pack(anchor="w", **pad)

        desc = ttk.Label(
            self,
            text=(
                "Abaixo estão as categorias e extensões que o sistema utiliza para diagnosticar no relatório PDF\n"
                "e para organizar fisicamente as pastas. Você pode exportar um modelo JSON, editá-lo e carregá-lo."
            ),
            wraplength=760
        )
        desc.pack(anchor="w", padx=14, pady=(0, 8))

        # 2. Barra de Botões de Ação
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", **pad)

        ttk.Button(
            btn_frame, text="📥 Carregar Configuração JSON", command=self._load_custom_json
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            btn_frame, text="📤 Exportar Modelo JSON", command=self._export_json
        ).pack(side="left", padx=6)

        ttk.Button(
            btn_frame, text="↺ Restaurar Padrões", command=self._restore_defaults
        ).pack(side="left", padx=6)

        # 3. Tabela (Treeview) de Categorias
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=14, pady=8)

        columns = ("categoria", "extensoes")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=12)
        self.tree.heading("categoria", text="Categoria", anchor="w")
        self.tree.heading("extensoes", text="Extensões Mapeadas", anchor="w")

        self.tree.column("categoria", width=180, stretch=False)
        self.tree.column("extensoes", width=550, stretch=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        # 4. Painel de Informações do Sistema
        info_frame = ttk.LabelFrame(self, text="Informações do Sistema Unificado")
        info_frame.pack(fill="x", **pad)

        info_text = (
            "• Versão: 2.0.0 (Unificação dos Projetos Disk Index + Organizador)\n"
            "• Compatibilidade: Linux e Windows (Executáveis autocontidos e scripts Python)\n"
            "• Motor PDF: Nativo vetorial puro (sem dependências externas)\n"
            "• Segurança: Logs de auditoria reversa automáticos em todas as movimentações."
        )
        ttk.Label(info_frame, text=info_text, justify="left").pack(anchor="w", padx=10, pady=8)

        self._populate_tree()

    def _populate_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for cat, exts in self.current_categories.items():
            ext_str = ", ".join(sorted(exts))
            self.tree.insert("", "end", values=(cat, ext_str))

    def _load_custom_json(self):
        path = filedialog.askopenfilename(
            title="Selecione o arquivo JSON de categorias",
            filetypes=[("Arquivos JSON", "*.json"), ("Todos os Arquivos", "*.*")]
        )
        if not path:
            return

        try:
            novas = carregar_categorias(path)
            self.current_categories = novas
            self._populate_tree()
            messagebox.showinfo(
                "Categorias Carregadas",
                f"Categorias carregadas com sucesso de:\n{path}\n\n{len(novas)} categorias ativas."
            )
        except Exception as e:
            messagebox.showerror("Erro ao Carregar", f"Falha ao processar arquivo JSON:\n{e}")

    def _export_json(self):
        path = filedialog.asksaveasfilename(
            title="Salvar modelo de categorias JSON",
            defaultextension=".json",
            filetypes=[("Arquivos JSON", "*.json")]
        )
        if not path:
            return

        try:
            salvar_categorias(path, self.current_categories)
            messagebox.showinfo("Exportado com Sucesso", f"Configuração exportada para:\n{path}")
        except Exception as e:
            messagebox.showerror("Erro ao Exportar", f"Não foi possível salvar o arquivo:\n{e}")

    def _restore_defaults(self):
        if messagebox.askyesno("Confirmar", "Deseja restaurar as categorias para a configuração padrão?"):
            self.current_categories = {k: list(v) for k, v in DEFAULT_CATEGORIES.items()}
            categories._atualizar_cache(self.current_categories)
            self._populate_tree()
            messagebox.showinfo("Restaurado", "Categorias padrão restauradas com sucesso.")
