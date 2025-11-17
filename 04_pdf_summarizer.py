try:
    import os
    import boto3
    import pandas as pd
    from pathlib import Path
    from botocore.exceptions import ClientError
    from botocore.config import Config
    from dotenv import load_dotenv
except ModuleNotFoundError as e:
    print(f"Erro: {e}")
    print("\nCrie e ative o ambiente virtual:")
    print("  python3 -m venv .venv")
    print("  source .venv/bin/activate  # No Windows: .venv\\Scripts\\activate")
    print("\nDepois instale as dependências:")
    print("  pip3 install -r requirements.txt")
    exit(1)

# Carregar variáveis do .env
load_dotenv()

# Configurações do .env
DATA_FOLDER = os.getenv('DATA_FOLDER')
TABLE_NAME = os.getenv('PDF_SEGMENTS_TABLE')
PROMPT_ARN = os.getenv('BEDROCK_PDF_SUMMARIZER_PROMPT_ARN')

# Configuração com timeout para PDFs
bedrock_config = Config(
    read_timeout=300,  # 5 minutos
    connect_timeout=60,
    retries={'max_attempts': 3, 'mode': 'adaptive'}
)

# Inicializar cliente AWS
bedrock_runtime_client = boto3.client("bedrock-runtime", config=bedrock_config)

def load_segments_table():
    """Carrega tabela de segmentos como DataFrame"""
    csv_path = os.path.join(DATA_FOLDER, TABLE_NAME)
    
    if not os.path.exists(csv_path):
        print(f"Arquivo CSV não encontrado: {csv_path}")
        print("Execute primeiro o script 03_pdf_splitter.py")
        exit(1)
    
    df = pd.read_csv(csv_path)
    
    # Adicionar coluna summary_path se não existir
    if 'summary_path' not in df.columns:
        df['summary_path'] = ''
        print("Coluna 'summary_path' adicionada à tabela")
    
    return df

def save_segments_table(df):
    """Salva DataFrame como CSV"""
    csv_path = os.path.join(DATA_FOLDER, TABLE_NAME)
    df.to_csv(csv_path, index=False)

def update_summary_path(df, segment_name, summary_path):
    """Atualiza summary_path no DataFrame e salva"""
    df.loc[df['segment_name'] == segment_name, 'summary_path'] = summary_path
    save_segments_table(df)

def sanitize_document_name(file_path):
    """Sanitiza o nome do documento para atender requisitos do Bedrock"""
    file_extension = os.path.splitext(file_path)[1][1:].lower()
    document_name = os.path.basename(file_path).replace(f".{file_extension}", "")
    
    import re
    document_name = re.sub(r'[^a-zA-Z0-9\s\-\(\)\[\]]', '-', document_name)
    document_name = re.sub(r'\s+', ' ', document_name)
    document_name = re.sub(r'-+', '-', document_name)
    document_name = document_name.strip(' -')
    
    return document_name

def generate_summary_with_bedrock(file_path):
    """Gera resumo usando AWS Bedrock"""
    
    print(f"Gerando resumo...")
    print(f"Arquivo: {file_path}")
    
    # Ler documento local
    with open(file_path, "rb") as f:
        doc_bytes = f.read()
    
    file_extension = os.path.splitext(file_path)[1][1:].lower()
    document_name = sanitize_document_name(file_path)
    
    print(f"Documento: {len(doc_bytes)} bytes ({len(doc_bytes) / 1024 / 1024:.2f} MB)")
    
    # Mensagem com documento local
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "document": {
                        "format": file_extension,
                        "name": document_name,
                        "source": {"bytes": doc_bytes}
                    }
                },
                {"text": "Generate a structured markdown summary from the document."}
            ]
        }
    ]
    
    try:
        print(f"Enviando requisição para Bedrock...")
        
        response = bedrock_runtime_client.converse(
            modelId=PROMPT_ARN,
            messages=messages
        )
        
        # Extrair resultado
        summary = response["output"]["message"]["content"][0]["text"]
        
        print(f"  Resumo gerado com sucesso ({len(summary)} caracteres)")
        return summary
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        print(f"  Erro: {error_code}")
        print(f"  Mensagem: {error_message}\n")
        print("  Sugestões:")
        
        if error_code == "ModelErrorException":
            print("  - Verifique se o arquivo PDF não está corrompido")
            print("  - Arquivos muito grandes podem exceder o limite de entrada do modelo")
            print("  - Tente com um arquivo menor primeiro")
        elif error_code == "ValidationException":
            print("  - O nome do arquivo contém caracteres inválidos")
            print("  - Renomeie o arquivo usando apenas: letras, números, espaços, hífens, parênteses e colchetes")
        elif error_code == "ThrottlingException":
            print("  - Muitas requisições simultâneas. Aguarde alguns segundos e tente novamente")
        
        return None
        
    except Exception as e:
        print(f"  Erro inesperado: {e}")
        return None

def save_summary(summary, segment_path, segment_name):
    """Salva o resumo como arquivo markdown na mesma pasta do segmento"""
    
    # Obter diretório do segmento PDF
    segment_dir = os.path.dirname(segment_path)
    
    # Gerar nome do arquivo markdown
    markdown_filename = f"{segment_name}.md"
    markdown_path = os.path.join(segment_dir, markdown_filename)
    
    # Salvar arquivo
    with open(markdown_path, "w", encoding="utf-8") as f:
        f.write(summary)
    
    print(f"  Resumo salvo em: {markdown_path}")
    return os.path.relpath(markdown_path, '.')

# Carregar tabela
df = load_segments_table()
print(f"Segmentos para processar: {len(df)}\n")

if df.empty:
    print("Nenhum segmento encontrado.")
    exit(1)

# Processar cada segmento
success_count = 0

for i, row in df.iterrows():
    print(f"\n[{i+1}/{len(df)}] Processando: {row['segment_name']}")
    
    # Verificar se já foi processado
    if pd.notna(row['summary_path']) and row['summary_path']:
        print(f"  Resumo já existe, pulando...")
        continue
    
    # Verificar se arquivo existe
    if not os.path.exists(row['segment_path']):
        print(f"  Arquivo não encontrado: {row['segment_path']}")
        continue
    
    # Gerar resumo
    summary = generate_summary_with_bedrock(row['segment_path'])
    
    if summary:
        # Salvar resumo
        summary_path = save_summary(summary, row['segment_path'], row['segment_name'])
        
        # Atualizar tabela imediatamente
        update_summary_path(df, row['segment_name'], summary_path)
        print(f"  Tabela atualizada com path: {summary_path}")
        
        success_count += 1
    else:
        print(f"  Falha ao gerar resumo para {row['segment_name']}")

print(f"\n=== Processamento Concluído ===")
print(f"Resumos gerados: {success_count}/{len(df)}")
print(f"Tabela: {os.path.join(DATA_FOLDER, TABLE_NAME)}")
