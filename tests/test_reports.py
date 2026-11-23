"""Testes unitários para geração de PDF nativo e exportação CSV."""

import os
import shutil
import tempfile
import unittest

from analista_organizador.core.scanner import scan
from analista_organizador.reports.csv_exporter import write_csv
from analista_organizador.reports.disk_report import build as build_pdf


class TestReports(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_reports_")

        # Criar dados de amostra
        with open(os.path.join(self.test_dir, "doc1.pdf"), "wb") as f:
            f.write(b"PDF SAMPLE CONTENT " * 100)
        with open(os.path.join(self.test_dir, "foto1.jpg"), "wb") as f:
            f.write(b"IMAGE SAMPLE CONTENT " * 200)

        self.out_dir = tempfile.mkdtemp(prefix="test_reports_out_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        shutil.rmtree(self.out_dir, ignore_errors=True)

    def test_pdf_generation(self):
        res = scan(self.test_dir)
        pdf_path = os.path.join(self.out_dir, "test_report.pdf")

        build_pdf(res, pdf_path)
        self.assertTrue(os.path.isfile(pdf_path))
        self.assertGreater(os.path.getsize(pdf_path), 500)

        with open(pdf_path, "rb") as f:
            header = f.read(8)
            self.assertTrue(header.startswith(b"%PDF-1.4"))

    def test_csv_export(self):
        res = scan(self.test_dir)
        csv_path = os.path.join(self.out_dir, "test_inventory.csv")

        n = write_csv(res, csv_path)
        self.assertEqual(n, 2)
        self.assertTrue(os.path.isfile(csv_path))

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            content = f.read()
            self.assertIn("caminho;pasta;arquivo", content)
            self.assertIn("doc1.pdf", content)
            self.assertIn("foto1.jpg", content)


if __name__ == "__main__":
    unittest.main()
