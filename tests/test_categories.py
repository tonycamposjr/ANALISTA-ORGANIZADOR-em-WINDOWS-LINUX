"""Testes unitários para o módulo de categorização."""

import json
import tempfile
from pathlib import Path
import unittest

from analista_organizador.core.categories import (
    DEFAULT_CATEGORIES,
    carregar_categorias,
    category_of,
    color_of,
    salvar_categorias,
)


class TestCategories(unittest.TestCase):
    def test_default_categories_lookup(self):
        self.assertEqual(category_of(".jpg"), "Imagens")
        self.assertEqual(category_of("PNG"), "Imagens")
        self.assertEqual(category_of(".mp4"), "Videos")
        self.assertEqual(category_of(".mp3"), "Audio")
        self.assertEqual(category_of(".pdf"), "Documentos")
        self.assertEqual(category_of(".xlsx"), "Planilhas")
        self.assertEqual(category_of(".pptx"), "Apresentacoes")
        self.assertEqual(category_of(".zip"), "Compactados")
        self.assertEqual(category_of(".exe"), "Instaladores")
        self.assertEqual(category_of(".py"), "Codigo")
        self.assertEqual(category_of(".ttf"), "Fontes")
        self.assertEqual(category_of(".psd"), "Design")
        self.assertEqual(category_of(".vdi"), "Maquinas Virtuais")
        self.assertEqual(category_of(".sqlite3"), "Banco de Dados")
        self.assertEqual(category_of(".desconhecido_xyz"), "Outros")
        self.assertEqual(category_of(""), "Sem extensao")
        self.assertEqual(category_of(None), "Sem extensao")

    def test_category_colors(self):
        cor_imagens = color_of("Imagens")
        self.assertIsInstance(cor_imagens, tuple)
        self.assertEqual(len(cor_imagens), 3)
        for c in cor_imagens:
            self.assertTrue(0.0 <= c <= 1.0)

        cor_outros = color_of("CategoriaInexistente")
        self.assertEqual(cor_outros, color_of("Outros"))

    def test_save_and_load_custom_categories(self):
        custom = {
            "Trabalho": [".doc", ".pdf"],
            "Midia": [".mp3", ".mp4"]
        }
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            salvar_categorias(temp_path, custom)
            carregadas = carregar_categorias(temp_path)
            self.assertIn("Trabalho", carregadas)
            self.assertIn("Midia", carregadas)
            self.assertIn(".doc", carregadas["Trabalho"])
            self.assertEqual(category_of(".doc", categories=carregadas), "Trabalho")
            self.assertEqual(category_of(".mp4", categories=carregadas), "Midia")
            self.assertEqual(category_of(".png", categories=carregadas), "Outros")
        finally:
            Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
