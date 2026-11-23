"""Testes unitários para o módulo de reversão (Undo / Rollback)."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from analista_organizador.core.organizer import organizar_pasta
from analista_organizador.core.undo import (
    desfazer,
    encontrar_log_mais_recente,
    encontrar_logs,
    ler_detalhes_log,
)


class TestUndo(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_undo_")

        # Criar arquivos iniciais
        self.file1 = os.path.join(self.test_dir, "documento.pdf")
        self.file2 = os.path.join(self.test_dir, "imagem.jpg")
        with open(self.file1, "w") as f:
            f.write("conteudo doc")
        with open(self.file2, "w") as f:
            f.write("conteudo img")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_full_organize_and_undo_cycle(self):
        # 1. Organizar os arquivos
        org_res = organizar_pasta(self.test_dir, dry_run=False)
        self.assertEqual(org_res.movidos, 2)
        self.assertIsNotNone(org_res.log_file)

        # Confirmar que saíram da raiz e foram para as pastas de categoria
        self.assertFalse(os.path.exists(self.file1))
        self.assertFalse(os.path.exists(self.file2))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Documentos", "documento.pdf")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Imagens", "imagem.jpg")))

        # 2. Localizar log e verificar metadados
        logs = encontrar_logs(self.test_dir)
        self.assertEqual(len(logs), 1)
        recent_log = encontrar_log_mais_recente(self.test_dir)
        self.assertEqual(recent_log, logs[0])

        details = ler_detalhes_log(recent_log)
        self.assertTrue(details["valido"])
        self.assertEqual(details["total_operacoes"], 2)

        # 3. Executar reversão (Undo)
        undo_res = desfazer(recent_log)
        self.assertEqual(undo_res.revertidos, 2)
        self.assertEqual(len(undo_res.erros), 0)

        # 4. Validar se os arquivos retornaram para a raiz
        self.assertTrue(os.path.exists(self.file1))
        self.assertTrue(os.path.exists(self.file2))


if __name__ == "__main__":
    unittest.main()
