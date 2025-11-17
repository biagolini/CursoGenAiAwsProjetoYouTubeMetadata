# Propósito

Gera uma tabela CSV com os vídeos mais recentes do canal do YouTube, criando a estrutura base para os próximos scripts da pipeline.

# O que o código faz

1. Conecta à YouTube Data API usando OAuth 2.0
2. Busca os vídeos mais recentes do canal
3. Extrai video_id e video_title
4. Ordena por título alfabeticamente
5. Cria colunas vazias para `material_link` e `bibliography_references`
6. Salva CSV com estrutura pronta para ser preenchida

# Saída

- **Arquivo**: `data/youtube_videos_table.csv`
- **Colunas**:
  - `video_id`: ID único do vídeo no YouTube
  - `video_title`: Título atual do vídeo no YouTube
  - `material_link`: Campo vazio (preenchido pelo script 06)
  - `bibliography_references`: Campo vazio (preenchimento manual)

# Configuração

- `YOUTUBE_MAX_VIDEOS`: Número de vídeos a buscar (padrão: 30)
- `YOUTUBE_VIDEOS_TABLE`: Nome do arquivo CSV (padrão: "youtube_videos_table.csv")
- `DATA_FOLDER`: Pasta onde salvar o CSV

# Pré-requisitos

- Arquivo `client_secret.json` (OAuth 2.0)
- Canal do YouTube ativo
- Dependências: `pip install google-auth google-auth-oauthlib google-api-python-client pandas`

# Próximo passo

Execute `06_content_source_matcher.py` para preencher a coluna `material_link` com a fonte de conteúdo desejada.
