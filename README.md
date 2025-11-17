# Treinamento AWS GenAI

Este repositório contém exemplos práticos de integração de serviços de IA Generativa da AWS, desenvolvido como material didático para um curso online de desenvolvimento de aplicações com GenAI na AWS.

## Objetivo

Este é um **projeto didático** focado em demonstrar como usar e integrar serviços serverless da AWS (Bedrock, Transcribe, Polly) com APIs externas (YouTube). O objetivo é educacional, não necessariamente representando a melhor arquitetura para produção.

## Sobre o Curso

O conteúdo foi desenvolvido no contexto de um curso de IA Generativa com serviços serverless na AWS. Este repositório está sendo divulgado antes da finalização do curso. O link para o curso será adicionado aqui em breve.

**Dúvidas ou sugestões?** Entre em contato via [LinkedIn](https://www.linkedin.com/in/biagolini)

## Licença e Uso

O código é **público e livre** para todos, incluindo aqueles que não são alunos do curso. Sinta-se à vontade para usar, modificar e aprender com os exemplos.

## Estrutura do Projeto

### Scripts Principais

- **01_transcribe.py** → Transcrição de áudio com AWS Transcribe
- **02_polly.py** → Síntese de voz com AWS Polly
- **03_pdf_splitter.py** → Divisão inteligente de PDFs por capítulos
- **04_pdf_summarizer.py** → Geração de resumos com AWS Bedrock
- **05_videos_table.py** → Coleta de vídeos do YouTube
- **06_content_source_matcher.py** → Matching de conteúdo (PDF/transcrição)
- **07_metadata_generator.py** → Geração de metadados multilíngues com Bedrock
- **08_update_youtube.py** → Aplicação de metadados no YouTube

### Organização de Pastas

- **input** → Arquivos de entrada fornecidos pelo usuário (não manipular após colocar)
- **output** → Saídas automáticas dos scripts (não manipular manualmente)
- **data** → Tabelas CSV e dados intermediários que podem precisar de intervenção manual
- **prompt** → Configurações de prompts do Bedrock

## Pré-requisitos

- **AWS CLI** instalado e configurado com credenciais
- **Python 3.x** instalado
- **Credenciais YouTube** (OAuth 2.0) para scripts 05-08

### Configuração do AWS CLI

Se precisar de ajuda para configurar o AWS CLI, assista à playlist completa no YouTube:

**[Como Configurar AWS CLI - Playlist Completa](https://youtube.com/playlist?list=PL-5Xgq4rqhTymYdKwWAwvd2keY_FFlLTl&si=iuT7obUW2SOFeCkt)**

## Instalação

### 1. Clone o Repositório

```bash
git clone https://github.com/biagolini/TreinamentoAwsGenAi.git
cd TreinamentoAwsGenAi
```

### 2. Crie e Ative um Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate
```

### 3. Instale as Dependências

```bash
pip3 install -r requirements.txt
```

### 4. Configure as Variáveis de Ambiente

```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas configurações:
- **AWS Transcribe**: Nome do bucket S3
- **AWS Bedrock**: ARNs dos prompts
- **YouTube API**: Configurações de vídeos e material
- **Outras configurações**: Ajuste conforme necessário

## Fluxo de Uso

### Pipeline de Processamento de PDFs

```bash
# 1. Dividir PDFs grandes por capítulos
python3 03_pdf_splitter.py

# 2. Gerar resumos dos segmentos (opcional)
python3 04_pdf_summarizer.py
```

### Pipeline de Metadados do YouTube

```bash
# 1. Coletar vídeos do canal
python3 05_videos_table.py

# 2. Fazer matching com conteúdo (PDF ou transcrição)
python3 06_content_source_matcher.py

# 3. Gerar metadados multilíngues com Bedrock
python3 07_metadata_generator.py

# 4. Aplicar metadados no YouTube
python3 08_update_youtube.py
```

## Importante

- Configure o arquivo `.env` antes de executar os scripts
- Mantenha suas credenciais AWS e YouTube em segurança
- Os serviços da AWS podem gerar custos - monitore seu uso
- Este é um projeto didático - adapte para suas necessidades de produção

## Contato

Para dúvidas, sugestões ou feedback:

**LinkedIn**: [https://www.linkedin.com/in/biagolini](https://www.linkedin.com/in/biagolini)
