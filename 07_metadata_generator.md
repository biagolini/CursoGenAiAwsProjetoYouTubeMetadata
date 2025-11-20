# Propósito

Gera metadados estruturados para vídeos do YouTube usando AWS Bedrock, com suporte multilíngue (português, inglês e espanhol). O código separa a geração de metadados da adição de referências e links adicionais.

# O que o código faz

1. Lê CSV com lista de vídeos e arquivos associados
2. **Verifica se existe transcrição** no formato `output/transcriptions/{video_id}.txt`
3. Envia arquivo para AWS Bedrock com prompt configurado
4. **Inclui transcrição formatada** se disponível: `<AUDIO-TRANSCRIPTION>conteúdo</AUDIO-TRANSCRIPTION>`
5. Extrai metadados estruturados via Tool Use (título, descrição, tags)
6. **Adiciona referências bibliográficas** da coluna `bibliography_references` (se existirem)
7. **Adiciona links adicionais** (canal e Medium) em todos os metadados
8. Adiciona data de publicação agendada
9. Salva JSON com metadados completos para todos os vídeos

# Saída

- **Arquivo**: `output/generated_metadata.json`
- **Estrutura**: JSON com metadados por video_id
- **Conteúdo**: Título, descrição (com referências e links), tags em 3 idiomas + data de publicação

# Configuração

## Variáveis do .env
- `YOUTUBE_VIDEOS_TABLE`: Nome do arquivo CSV com vídeos
- `BEDROCK_METADATA_GENERATOR_PROMPT_ARN`: ARN do prompt no Bedrock
- `METADATA_START_DATE`: Data inicial de publicação (YYYY-MM-DD)
- `METADATA_INTERVAL_DAYS`: Intervalo entre publicações (dias)
- `METADATA_PUBLISH_TIME`: Horário de publicação (formato: "T16:30:00Z")
- `METADATA_OUTPUT_FILE`: Caminho do arquivo JSON de saída
- `METADATA_MAX_RETRIES`: Número máximo de tentativas em caso de erro (padrão: 3)

## Links Configurados no Código
- Canal de tutoriais: `https://www.youtube.com/@BiagoliniTech`
- Artigos Medium: `https://medium.com/@biagolini`

# Estrutura do CSV

Colunas obrigatórias:
- `video_id`: ID único do vídeo
- `video_title`: Título do vídeo
- `material_link`: Caminho para o arquivo (PDF/MD/TXT)
- `bibliography_references`: Links separados por espaço (opcional)

# Transcrições (Opcional)

O código automaticamente procura por arquivos de transcrição em:
- **Pasta**: `output/transcriptions/`
- **Formato**: `{video_id}.txt`
- **Conteúdo**: Texto da transcrição do áudio/vídeo

Se encontrado, a transcrição é formatada e enviada junto com o documento:
```
The following context is the transcription of the audio content. Please note that there may be errors due to transcription inaccuracies:

<AUDIO-TRANSCRIPTION>
[conteúdo da transcrição]
</AUDIO-TRANSCRIPTION>
```

# Processamento de Referências

## Com Referências
```
Descrição original...

Referências:
- https://docs.aws.amazon.com/link1
- https://docs.aws.amazon.com/link2

Conheça meu outro canal...
Leia mais artigos em...
```

## Sem Referências
```
Descrição original...

Conheça meu outro canal...
Leia mais artigos em...
```

# Prompt Configuration

Detalhes completos da configuração do prompt estão disponíveis em:
- `prompt/metadata_generator/prompt_pt.md`: Configuração em português (default)
- `prompt/metadata_generator/prompt_en.md`: Configuração em inglês (default)
- `prompt/metadata_generator/tool_schema.json`: Schema JSON da ferramenta

**Importante**: Os prompts foram atualizados para NÃO incluir links ou referências durante a geração. Estes são adicionados programaticamente após a geração.

# Pré-requisitos

- AWS CLI configurado com credenciais
- Prompt criado no Bedrock Prompt Manager
- CSV com estrutura correta (gerado pelos scripts 05 e 06)
- Arquivos nos caminhos especificados no CSV
- Dependências: `pip install boto3 pandas python-dotenv`

# Tratamento de Erros

O código trata automaticamente:
- **ModelErrorException**: Limites de tokens excedidos
- **ValidationException**: Nomes de arquivo com caracteres inválidos
- **ThrottlingException**: Muitas requisições simultâneas
- **Vídeos já processados**: Pula automaticamente

## Sistema de Retry e Fallback

1. **Retry automático**: Tenta até `METADATA_MAX_RETRIES` vezes (padrão: 3)
2. **Fallback genérico**: Se todas as tentativas falharem, usa metadados genéricos:
   - **Título**: "Aprenda AWS: Guia Prático" (pt/en/es)
   - **Descrição**: Texto genérico sobre AWS em cada idioma
   - **Tags**: ["AWS", "Cloud", "Tutorial", "Technology", "Development"]
3. **Garantia de continuidade**: Nunca pula datas de publicação
4. **Truncamento automático**: Descrições são limitadas a 5000 caracteres, cortando no último ". " (ponto + espaço)

Nomes de arquivo são sanitizados automaticamente para atender requisitos do Bedrock.

# Próximo passo

Execute `08_update_youtube.py` para aplicar os metadados gerados aos vídeos do YouTube.
