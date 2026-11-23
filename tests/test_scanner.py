"""Testes unitários para o módulo de varredura (scanner)."""

import os
import shutil
import tempfile
import unittest

from analista_organizador.core.scanner import (
    human,
    human_time,
    scan,
    ScanProgress,
)


class TestScanner(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_scanner_")

        # Criar estrutura de arquivos de teste
        # Pasta A
        pasta_a = os.path.join(self.test_dir, "Imagens")
        os.makedirs(pasta_a, exist_ok=True)
        with open(os.path.join(pasta_a, "foto1.jpg"), "wb") as f:
            f.write(b"ABCDEF123456" * 100)

        # Pasta B com duplicata de mesmo nome e tamanho
        pasta_b = os.path.join(self.test_dir, "TempData")
        os.makedirs(pasta_b, exist_ok=True)
        with open(os.path.join(pasta_b, "foto1.jpg"), "wb") as f:
            f.write(b"ABCDEF123456" * 100)  # duplicata idêntica (mesmo nome e tamanho)

        with open(os.path.join(pasta_b, "backup.bak"), "wb") as f:
            f.write(b"temp data" * 20)

        # Arquivo solto na raiz
        with open(os.path.join(self.test_dir, "documento.pdf"), "wb") as f:
            f.write(b"%PDF-1.4 mock content" * 50)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_human_formatting(self):
        self.assertEqual(human(500), "500 B")
        self.assertEqual(human(2048), "2,0 KB")
        self.assertEqual(human(1024 * 1024 * 5), "5,0 MB")
        self.assertEqual(human(1024 * 1024 * 1024 * 3.5), "3,5 GB")

    def test_human_time(self):
        self.assertEqual(human_time(45), "45s")
        self.assertEqual(human_time(90), "1m30s")
        self.assertEqual(human_time(3665), "1h01m")

    def test_scan_and_duplicates(self):
        res = scan(self.test_dir, dup_mode="rapido", big_threshold=100)
        self.assertEqual(res.total_files, 4)
        self.assertGreater(res.total_size, 0)
        self.assertIn("Imagens", res.by_cat)
        self.assertIn(".jpg", res.by_ext)
        self.assertEqual(len(res.root_files), 1)
        self.assertEqual(res.root_files[0][1], "documento.pdf")

        # Testar detecção de duplicados
        self.assertGreaterEqual(len(res.dup_groups), 1)

        # Testar candidatos a limpeza (.bak)
        self.assertTrue(any("Temporarios" in k for k in res.cleanup.keys()))

    def test_scan_modes(self):
        res_parcial = scan(self.test_dir, dup_mode="parcial", big_threshold=1000)
        self.assertEqual(res_parcial.total_files, 4)

        res_completo = scan(self.test_dir, dup_mode="completo", big_threshold=1000)
        self.assertEqual(res_completo.total_files, 4)


if __name__ == "__main__":
    unittest.main()
