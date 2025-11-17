try:
    import time
    import os
    import json
    import sys
    from pathlib import Path
    import boto3
    import pandas as pd
    from botocore.exceptions import NoCredentialsError
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

# Constantes do .env
INPUT_CSV = os.getenv('TRANSCRIBE_INPUT_CSV')
LOCAL_OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER')
FILE_PATH_COLUMN = os.getenv('TRANSCRIBE_FILE_PATH_COLUMN')

BUCKET_NAME = os.getenv('TRANSCRIBE_BUCKET_NAME')
S3_INPUT_PREFIX = os.getenv('TRANSCRIBE_S3_INPUT_PREFIX')
S3_OUTPUT_PREFIX = os.getenv('TRANSCRIBE_S3_OUTPUT_PREFIX')

MEDIA_FORMAT = os.getenv('TRANSCRIBE_MEDIA_FORMAT')
LANGUAGE_CODE = os.getenv('TRANSCRIBE_LANGUAGE_CODE')

def check_aws_credentials():
    """Verifica se há credenciais AWS válidas"""
    try:
        sts = boto3.client('sts')
        sts.get_caller_identity()
    except NoCredentialsError:
        print("Credenciais AWS não encontradas.")
        print("\nFaça login com: aws sso login --sso-session <nome-da-sessao>")
        print("Depois defina: export AWS_PROFILE=<nome-do-perfil>")
        print("\nEm caso de dúvidas, veja os vídeos de configuração da AWS CLI")
        print("(disponíveis para Windows, Ubuntu e MacOS)")
        sys.exit(1)
    except Exception as e:
        print(f"Erro ao validar credenciais AWS: {e}")
        print("\nFaça login com: aws sso login --sso-session <nome-da-sessao>")
        print("Depois defina: export AWS_PROFILE=<nome-do-perfil>")
        print("\nEm caso de dúvidas, veja os vídeos de configuração da AWS CLI")
        print("(disponíveis para Windows, Ubuntu e MacOS)")
        sys.exit(1)

check_aws_credentials()

# Verificar se arquivo CSV existe
if not os.path.exists(INPUT_CSV):
    print(f"Arquivo {INPUT_CSV} não encontrado. Encerrando.")
    exit(1)

# Criar pasta de output
os.makedirs(LOCAL_OUTPUT_FOLDER, exist_ok=True)

# Inicializar clientes AWS
s3_client = boto3.client('s3')
transcribe_client = boto3.client('transcribe')

# Ler arquivos do CSV com pandas
df = pd.read_csv(INPUT_CSV)
files_to_process = df[FILE_PATH_COLUMN].tolist()

print(f"Encontrados {len(files_to_process)} arquivos para processar")

# 1. Upload de todos os arquivos
print("\n=== Iniciando uploads ===")
for file_path in files_to_process:
    if not os.path.exists(file_path):
        print(f"Arquivo {file_path} não encontrado, pulando...")
        continue
    
    file_name = os.path.basename(file_path)
    s3_key = f"{S3_INPUT_PREFIX}{file_name}"
    
    print(f"Uploading {file_name}...")
    s3_client.upload_file(
        Filename=file_path,
        Bucket=BUCKET_NAME,
        Key=s3_key
    )
    print(f"[OK] {file_name} enviado")

# 2. Iniciar jobs de transcrição
print("\n=== Iniciando jobs de transcrição ===")
jobs = {}
for file_path in files_to_process:
    if not os.path.exists(file_path):
        continue
    
    file_name = os.path.basename(file_path)
    s3_key = f"{S3_INPUT_PREFIX}{file_name}"
    job_name = f"transcribe-{Path(file_name).stem}-{int(time.time())}"
    
    print(f"Iniciando job: {job_name}")
    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': f's3://{BUCKET_NAME}/{s3_key}'},
        MediaFormat=MEDIA_FORMAT,
        LanguageCode=LANGUAGE_CODE,
        OutputBucketName=BUCKET_NAME,
        OutputKey=S3_OUTPUT_PREFIX
    )
    
    jobs[job_name] = file_name
    print(f"[OK] Job {job_name} iniciado")

# 3. Aguardar conclusão dos jobs
print("\n=== Aguardando conclusão dos jobs ===")
pending_jobs = set(jobs.keys())

while pending_jobs:
    print(f"\nJobs pendentes: {len(pending_jobs)}")
    completed = []
    
    for job_name in pending_jobs:
        status_response = transcribe_client.get_transcription_job(
            TranscriptionJobName=job_name
        )
        status = status_response['TranscriptionJob']['TranscriptionJobStatus']
        
        if status == 'COMPLETED':
            print(f"[OK] {job_name} concluído")
            completed.append(job_name)
        elif status == 'FAILED':
            print(f"[ERRO] {job_name} falhou")
            completed.append(job_name)
        else:
            print(f"{job_name} ainda processando...")
    
    # Remover jobs concluídos
    for job_name in completed:
        pending_jobs.remove(job_name)
    
    if pending_jobs:
        time.sleep(10)

# 4. Download e extração das transcrições
print("\n=== Baixando transcrições ===")
for job_name, file_name in jobs.items():
    s3_output_key = f'{S3_OUTPUT_PREFIX}{job_name}.json'
    local_json = os.path.join(LOCAL_OUTPUT_FOLDER, f'{job_name}.json')
    local_txt = os.path.join(LOCAL_OUTPUT_FOLDER, f'{Path(file_name).stem}.txt')
    
    try:
        # Download do JSON
        s3_client.download_file(
            Bucket=BUCKET_NAME,
            Key=s3_output_key,
            Filename=local_json
        )
        
        # Extrair texto
        with open(local_json, 'r', encoding='utf-8') as f:
            transcription_data = json.load(f)
        
        transcript_text = transcription_data['results']['transcripts'][0]['transcript']
        
        # Salvar TXT
        with open(local_txt, 'w', encoding='utf-8') as f:
            f.write(transcript_text)
        
        print(f"[OK] {file_name} -> {Path(file_name).stem}.txt")
    except Exception as e:
        print(f"[ERRO] Erro ao processar {job_name}: {e}")

print("\n=== Processamento concluído ===")
