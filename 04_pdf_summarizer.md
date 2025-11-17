# PDF Summarizer - Gerador de Resumos

Este script processa arquivos PDF e gera resumos estruturados em formato markdown usando AWS Bedrock.

## Funcionalidade

O `04_pdf_summarizer.py` complementa o `03_pdf_splitter.py` oferecendo uma alternativa para trabalhar com PDFs:

1. **Processa segmentos PDF**: Lê arquivos da tabela `pdf_segments_table.csv`
2. **Gera Resumos**: Usa AWS Bedrock para criar resumos estruturados
3. **Salva Markdown**: Armazena resumos na mesma pasta do segmento PDF
4. **Atualiza Tabela**: Adiciona coluna `summary_path` com caminho dos resumos

## Estrutura dos Resumos

Cada resumo gerado segue estrutura markdown definida pelo prompt do Bedrock.

## Configuração

### Pré-requisitos

- AWS CLI configurado com credenciais válidas
- Prompt configurado no Bedrock Prompt Manager
- Tabela `pdf_segments_table.csv` gerada pelo script 03

### Estrutura de Pastas

```
├── output/          # Segmentos PDF e resumos
├── data/            # Tabela CSV
└── 04_pdf_summarizer.py
```

## Como Usar

### 1. Preparar Segmentos

```bash
# Executar script de divisão de PDFs primeiro
python3 03_pdf_splitter.py
```

### 2. Executar o Script

```bash
python3 04_pdf_summarizer.py
```

### 3. Verificar Resultados

Os resumos serão salvos na mesma pasta dos segmentos PDF com extensão `.md`.

## Exemplo de Uso no Fluxo

### Cenário: Usar resumos para metadados
```bash
# 1. Dividir PDF grande
python3 03_pdf_splitter.py

# 2. Gerar resumos dos segmentos
python3 04_pdf_summarizer.py

# 3. Criar tabela de vídeos
python3 05_videos_table.py

# 4. Fazer matching com resumos
# Configurar YOUTUBE_MATERIAL_SOURCE=pdf_summary no .env
python3 06_content_source_matcher.py

# 5. Gerar metadados usando resumos
python3 07_metadata_generator.py
```

## Configurações

### Variáveis do .env
- `DATA_FOLDER`: Pasta da tabela CSV
- `PDF_SEGMENTS_TABLE`: Nome da tabela de segmentos
- `BEDROCK_PDF_SUMMARIZER_PROMPT_ARN`: ARN do prompt no Bedrock

### Timeout e Retry
```python
bedrock_config = Config(
    read_timeout=300,  # 5 minutos
    connect_timeout=60,
    retries={'max_attempts': 3, 'mode': 'adaptive'}
)
```

## Tratamento de Erros

O script trata automaticamente:

- **ModelErrorException**: Arquivo corrompido ou muito grande
- **ValidationException**: Nome de arquivo com caracteres inválidos
- **ThrottlingException**: Muitas requisições simultâneas
- **Arquivos já processados**: Pula automaticamente

## Limitações

- **Tamanho do arquivo**: Limitado pelo modelo Bedrock
- **Formato**: Apenas arquivos PDF
- **Caracteres no nome**: Apenas alfanuméricos, espaços, hífens, parênteses e colchetes

## Integração com Outros Scripts

Este script se integra com:

- **03_pdf_splitter.py**: Usa tabela de segmentos gerada
- **06_content_source_matcher.py**: Fornece resumos para matching
- **07_metadata_generator.py**: Resumos são usados para gerar metadados

## Troubleshooting

### Erro de Credenciais AWS
```bash
aws configure
# ou
export AWS_PROFILE=seu-perfil
```

### Arquivo muito grande
- Ajuste `PDF_MAX_FILE_SIZE_MB` no .env
- Reduza `PDF_MAX_PAGES` no .env
- Use `PDF_REMOVE_IMAGES=True` para comprimir

### Caracteres inválidos no nome
- O script sanitiza automaticamente
- Se persistir, renomeie arquivos manualmente
