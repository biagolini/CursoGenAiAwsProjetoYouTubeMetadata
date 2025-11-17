# Propósito

Preenche a coluna `material_link` da tabela de vídeos com base na fonte de conteúdo escolhida: transcrições do YouTube, segmentos de PDF ou resumos de PDF.

# O que o código faz

1. Carrega a tabela de vídeos gerada pelo script `05_videos_table.py`
2. Verifica a variável `YOUTUBE_MATERIAL_SOURCE` para determinar a fonte
3. Executa o fluxo apropriado:
   - **transcription**: Busca legendas do YouTube via API, processa SRT e salva como TXT
   - **pdf_segment**: Faz matching com `segment_path` da tabela de PDFs
   - **pdf_summary**: Faz matching com `summary_path` da tabela de PDFs
4. Atualiza a coluna `material_link` na tabela
5. Salva progresso automaticamente

# Fontes de Material

## Transcrição do YouTube (transcription)
- Busca legendas disponíveis via YouTube Data API
- Prioriza idiomas configurados em `YOUTUBE_TRANSCRIPTION_LANGUAGES`
- Baixa formato SRT e converte para texto puro
- Salva em `output/youtube_transcriptions/{video_id}.txt`
- **Limitação**: Sujeito a quotas da API do YouTube (aproximadamente 10.000 unidades/dia)

## Segmento de PDF (pdf_segment)
- Faz matching entre título do vídeo e nome do segmento PDF
- Usa normalização de texto (remove `_`, `-`, `()`, `[]`, `.`)
- Preenche com caminho do arquivo PDF original
- Requer tabela `pdf_segments_table.csv` gerada pelo script `03_pdf_splitter.py`

## Resumo de PDF (pdf_summary)
- Faz matching entre título do vídeo e nome do segmento PDF
- Usa normalização de texto (remove `_`, `-`, `()`, `[]`, `.`)
- Preenche com caminho do arquivo markdown de resumo
- Requer tabela `pdf_segments_table.csv` com coluna `summary_path` preenchida pelo script `04_pdf_summarizer.py`

# Saída

- **Arquivo atualizado**: `data/youtube_videos_table.csv`
- **Arquivos de transcrição** (se `YOUTUBE_MATERIAL_SOURCE=transcription`): `output/youtube_transcriptions/*.txt`

# Configuração

- `YOUTUBE_MATERIAL_SOURCE`: Fonte de material (`transcription`, `pdf_segment`, `pdf_summary`)
- `YOUTUBE_TRANSCRIPTION_LANGUAGES`: Idiomas preferidos para legendas (ex: `pt,en,es`)
- `YOUTUBE_VIDEOS_TABLE`: Nome do arquivo CSV da tabela de vídeos
- `PDF_SEGMENTS_TABLE`: Nome do arquivo CSV da tabela de PDFs

# Limitações da API do YouTube

A YouTube Data API tem quota diária de aproximadamente 10.000 unidades. Operações de legenda consomem:
- `captions.list`: 50 unidades por chamada
- `captions.download`: 200 unidades por chamada

**Total por vídeo**: ~250 unidades (aproximadamente 40 vídeos por dia)

Se atingir o limite de quota:
- O script marca vídeos como `ERRO_AO_BUSCAR_TRANSCRICAO`
- Execute novamente no dia seguinte para processar os restantes
- O script pula vídeos já processados automaticamente

# Pré-requisitos

- Tabela de vídeos gerada pelo `05_videos_table.py`
- Arquivo `client_secret.json` (OAuth 2.0) - apenas para `transcription`
- Tabela `pdf_segments_table.csv` - apenas para `pdf_segment` ou `pdf_summary`
- Dependências: `pip install google-auth google-auth-oauthlib google-api-python-client pandas`

# Tratamento de Erros

- **Vídeos sem legenda**: Marca como `TRANSCRICAO_NAO_ENCONTRADA`
- **Quota excedida**: Marca como `ERRO_AO_BUSCAR_TRANSCRICAO` (execute novamente depois)
- **Sem match de PDF**: Marca como `ADICIONAR_NOME_ARQUIVO_MANUALMENTE`
- **Arquivo já existe**: Pula download e apenas atualiza referência
