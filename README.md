# Analista & Organizador de Arquivos

**Sistema Multiplataforma de Diagnóstico de Armazenamento, Relatórios Executivos em PDF/CSV, Organização Inteligente e Auditoria Reversa.**

---

## 1. Visão Geral

O **Analista & Organizador de Arquivos** é o resultado da unificação arquitetural completa de dois sistemas independentes em um único software profissional:
1. **Disk Index (Analista de Disco):** Análise profunda de unidades e diretórios, estatísticas de uso, identificação de arquivos gigantes, detecção avançada de duplicados (SHA-256) e geração de relatórios vetoriais em PDF nativo e inventário CSV.
2. **Organizador de Arquivos:** Organização estruturada de arquivos em categorias temáticas, criação de subpastas por data (Ano/Mês), modo de simulação (*Dry-Run*), isolamento de duplicatas e auditoria reversa (*Rollback*) para restaurar arquivos ao estado original.

O sistema opera de forma totalmente independente de bibliotecas de terceiros em tempo de execução, garantindo portabilidade em qualquer ambiente com Python 3.8+ e Tkinter. Executáveis autocontidos para Windows e Linux também estão disponíveis.

---

## 2. Principais Funcionalidades

### 📊 Módulo Analisador (Disk Index)
- **Diagnóstico Completo:** Estatísticas de capacidade usada, livre e total, contagem de pastas e tipos de arquivos.
- **Detecção de Duplicados em 3 Níveis:**
  - `rapido`: Comparação de nome e tamanho (instantâneo).
  - `parcial`: Nome, tamanho e hash SHA-256 do início e fim do arquivo (128 KB).
  - `completo`: Hash SHA-256 integral do arquivo lido em blocos de 1 MB.
- **Relatório PDF Nativo Vetorial:**
  - Gera PDF-1.4 sem ReportLab ou bibliotecas externas.
  - Cartões de resumo executivo, gráficos de barras de distribuição por categoria, tabela de estrutura em 3 níveis hierárquicos, maiores arquivos e ranking de extensões.
  - **Índice/Bookmarks clicáveis** no visualizador de PDF para saltar entre seções.
- **Inventário CSV:** Exportação estruturada (UTF-8 com BOM) delimitada por ponto e vírgula, pronta para abertura no Excel e LibreOffice Calc.
- **Candidatos à Limpeza:** Localização de arquivos temporários (`.tmp`, `.bak`), logs, estados de VM (`.vmem`), instaladores residuais e arquivos de 0 bytes.

### 🗂️ Módulo Organizador
- **Classificação Inteligente:** Separação automática em 13 categorias temáticas (Imagens, Vídeos, Áudio, Documentos, Planilhas, Apresentações, Compactados, Instaladores, Código, Fontes, Design, Máquinas Virtuais, Banco de Dados).
- **Modo Simulação (Dry-Run):** Permite visualizar tudo o que seria movido antes de realizar qualquer alteração física no disco.
- **Organização Temporal:** Criação opcional de subpastas `Ano/Mês` com base na data de modificação dos arquivos.
- **Isolamento de Duplicatas:** Detecção de conteúdo idêntico por hash seguro e movimentação das cópias para a pasta `Duplicados/`.
- **Tratamento Anti-Colisão:** Prevenção de sobrescrita renomeando conflitos para `arquivo (1).ext`.

### 🔄 Módulo de Auditoria Reversa (Rollback / Desfazer)
- **Log de Auditoria em JSON:** Cada organização gera automaticamente um arquivo `_organizacao_log_AAAAMMDD_HHMMSS.json` contendo o mapa de todas as movimentações.
- **Restauração Segura:** Reverte as operações em ordem inversa (LIFO), recriando pastas de origem e restaurando cada arquivo ao seu ponto original com proteção anti-sobrescrita (`(restaurado N)`).

### ⚙️ Gestão de Categorias e Configurações
- **Personalização por JSON:** Exportação e importação de modelos de categorias personalizados para fluxos de trabalho específicos.
- **Persistência Centralizada:** Armazenamento automático das últimas preferências do usuário em `~/.config/analista-organizador/config.json`.

---

## 3. Arquitetura do Sistema

```
ANALISTA-ORGANIZADOR antigravity/
├── analista_organizador/
│   ├── __init__.py               # Metadados e exports públicos
│   ├── config.py                 # Gerenciamento de configurações centralizadas
│   ├── core/
│   │   ├── __init__.py
│   │   ├── categories.py         # Mapeamento de categorias, cores RGB e parser JSON
│   │   ├── scanner.py            # Motor de varredura recursiva, duplicatas e limpeza
│   │   ├── organizer.py          # Motor de organização, resolução de conflitos, dry-run
│   │   └── undo.py               # Motor de auditoria reversa e rollback
│   ├── reports/
│   │   ├── __init__.py
│   │   ├── pdf_writer.py         # Escritor vetorial nativo em formato PDF-1.4
│   │   ├── disk_report.py        # Orquestrador das seções do relatório executivo
│   │   └── csv_exporter.py       # Exportador do inventário CSV com UTF-8 BOM
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── app.py                # Janela principal Tkinter com sistema de abas
│   │   ├── tab_analyst.py        # Aba do Analisador (Disk Index, PDF, CSV)
│   │   ├── tab_organizer.py      # Aba do Organizador (Dry-Run, Data, Duplicados)
│   │   ├── tab_undo.py           # Aba de Desfazer e Histórico de Logs
│   │   ├── tab_settings.py       # Aba de Configurações e Categorias
│   │   └── widgets.py            # Componentes visuais reutilizáveis (FolderPicker, LogBox)
│   └── cli/
│       ├── __init__.py
│       └── main.py               # Despachante CLI com subcomandos
├── config_categorias_padrao.json # Modelo padrão de categorias em formato JSON
├── run.py                        # Ponto de entrada universal (GUI e CLI)
├── build_linux.sh                # Script de compilação para Linux (PyInstaller)
├── build_windows.bat             # Script de compilação para Windows (PyInstaller)
├── AnalistaOrganizador.spec      # Spec PyInstaller para versão GUI
├── AnalistaOrganizadorCLI.spec   # Spec PyInstaller para versão CLI
├── tests/                        # Suite de testes automatizados
│   ├── test_categories.py
│   ├── test_organizer.py
│   ├── test_reports.py
│   ├── test_scanner.py
│   └── test_undo.py
└── README.md
```

---

## 4. Como Executar

### 4.1 Interface Gráfica (Padrão)

Para abrir a interface gráfica completa com abas integradas:

```bash
python3 run.py
# ou
python3 run.py gui
```

No Windows:
```cmd
python run.py
```

### 4.2 Linha de Comando (CLI)

O aplicativo conta com uma CLI completa e intuitiva baseada em subcomandos:

#### A. Analisar Disco / Pasta e Gerar Relatórios
```bash
python3 run.py analisar /caminho/da/pasta -o relatorio.pdf --dup-mode parcial
```
*Opções:*
- `-o, --output`: Caminho do PDF de saída (padrão: `~/indice_<pasta>.pdf`).
- `--min-mb 50`: Listar arquivos com tamanho maior ou igual a N MB (padrão: 50).
- `--dup-mode off|rapido|parcial|completo`: Nível de detecção de duplicatas (padrão: `rapido`).
- `--no-csv`: Desativa a geração do inventário CSV.
- `--csv-out`: Caminho do CSV de saída.
- `--quiet`: Desativa a barra de progresso no terminal.

*Compatibilidade Retroativa:* O comando aceita o formato legado `--cli /caminho`.

#### B. Organizar Conteúdo de uma Pasta
```bash
# Simulação prévia (Dry-Run recomendado):
python3 run.py organizar /caminho/Downloads --dry-run

# Organização real criando subpastas por data e isolando duplicados:
python3 run.py organizar /caminho/Downloads --por-data --duplicados
```
*Opções:*
- `--dry-run`: Exibe o que seria movido sem alterar arquivos.
- `--por-data`: Organiza em subpastas `Ano/Mês` dentro de cada categoria.
- `--duplicados`: Move réplicas de mesmo conteúdo para a pasta `Duplicados/`.
- `--config meu_config.json`: Utiliza categorias personalizadas.
- `--sim`: Pula a confirmação interativa no terminal.

#### C. Desfazer Organização (Rollback)
```bash
# Localiza automaticamente o log mais recente da pasta e reverte:
python3 run.py desfazer /caminho/Downloads

# Reverter a partir de um log específico:
python3 run.py desfazer /caminho/Downloads --log _organizacao_log_20261123_150000.json
```

#### D. Consultar e Exportar Categorias
```bash
# Listar categorias e extensões no terminal:
python3 run.py categorias --listar

# Exportar modelo JSON de categorias para edição:
python3 run.py categorias --exportar minhas_categorias.json
```

---

## 5. Compilação de Executáveis Standalone (Build)

O software pode ser empacotado em executáveis binários autocontidos, permitindo distribuição sem necessidade de instalar o Python na máquina do usuário final.

### No Linux:
```bash
./build_linux.sh
```
Os executáveis serão gerados em `dist_linux/`:
- `dist_linux/AnalistaOrganizador` (Interface Gráfica)
- `dist_linux/AnalistaOrganizadorCLI` (Linha de Comando)

### No Windows:
Execute com duplo clique ou via terminal:
```cmd
build_windows.bat
```
Os executáveis serão gerados em `dist_windows\`:
- `dist_windows\AnalistaOrganizador.exe` (Interface Gráfica)
- `dist_windows\AnalistaOrganizadorCLI.exe` (Linha de Comando)

---

## 6. Testes Automatizados

Para executar toda a bateria de testes unitários:

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

---

## 7. Licença e Autoria

Projeto unificado e otimizado por **Tony & Google Antigravity (AGY)**.
Uso livre para organização pessoal, diagnóstico de storage e gestão de infraestrutura.
