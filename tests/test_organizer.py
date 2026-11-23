"""Testes unitários para o módulo de organização física de arquivos."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from analista_organizador.core.organizer import (
    destino_sem_conflito,
    eh_arquivo_ignorado,
    organizar_pasta,
)


class TestOrganizer(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_organizer_")

        # Criar arquivos para organizar
        with open(os.path.join(self.test_dir, "foto.png"), "w") as f:
            f.write("conteudo foto")
        with open(os.path.join(self.test_dir, "relatorio.pdf"), "w") as f:
            f.write("conteudo relatorio")
        with open(os.path.join(self.test_dir, "script.py"), "w") as f:
            f.write("print('hello')")
        with open(os.path.join(self.test_dir, "desktop.ini"), "w") as f:
            f.write("ignored")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_eh_arquivo_ignorado(self):
        self.assertTrue(eh_arquivo_ignorado(".DS_Store"))
        self.assertTrue(eh_arquivo_ignorado("desktop.ini"))
        self.assertTrue(eh_arquivo_ignorado(".git"))
        self.assertFalse(eh_arquivo_ignorado("documento.pdf"))

    def test_destino_sem_conflito(self):
        dest_dir = Path(self.test_dir) / "Destino"
        dest_dir.mkdir(parents=True, exist_ok=True)

        target1 = destino_sem_conflito(dest_dir, "teste.txt")
        self.assertEqual(target1.name, "teste.txt")

        # Cria o arquivo para forçar colisão
        with open(target1, "w") as f:
            f.write("x")

        target2 = destino_sem_conflito(dest_dir, "teste.txt")
        self.assertEqual(target2.name, "teste (1).txt")

    def test_organizar_dry_run(self):
        res = organizar_pasta(self.test_dir, dry_run=True)
        self.assertTrue(res.dry_run)
        self.assertEqual(res.movidos, 3)  # foto.png, relatorio.pdf, script.py
        # Nenhum arquivo deve ter sido movido de verdade
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "foto.png")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "relatorio.pdf")))
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "Imagens")))

    def test_organizar_de_verdade(self):
        res = organizar_pasta(self.test_dir, dry_run=False)
        self.assertFalse(res.dry_run)
        self.assertEqual(res.movidos, 3)

        # Verificar se foram movidos para as categorias correspondentes
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Imagens", "foto.png")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Documentos", "relatorio.pdf")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Codigo", "script.py")))
        # desktop.ini não deve ter sido movido
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "desktop.ini")))

        # Verificar se arquivo de log foi gerado
        self.assertIsNotNone(res.log_file)
        self.assertTrue(res.log_file.is_file())


if __name__ == "__main__":
    unittest.main()
