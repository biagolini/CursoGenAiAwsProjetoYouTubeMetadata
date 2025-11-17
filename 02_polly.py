try:
    import os
    import re
    import sys
    from pathlib import Path
    from collections import defaultdict
    import boto3
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
INPUT_FOLDER = os.getenv('INPUT_FOLDER')
OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER')
VOICE_ID = os.getenv('POLLY_VOICE_ID')
LANGUAGE_CODE = os.getenv('POLLY_LANGUAGE_CODE')
ENGINE = os.getenv('POLLY_ENGINE')
OUTPUT_FORMAT = os.getenv('POLLY_OUTPUT_FORMAT')

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

# Criar pasta de output
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Inicializar cliente Polly
polly_client = boto3.client('polly')

# Padrão para identificar arquivos vXXsXX.txt
pattern = re.compile(r'^v(\d+)s(\d+)\.txt$')

# Coletar arquivos válidos
files_data = []
for filename in os.listdir(INPUT_FOLDER):
    match = pattern.match(filename)
    if match:
        video_id = int(match.group(1))
        section_id = int(match.group(2))
        files_data.append({
            'filename': filename,
            'video_id': video_id,
            'section_id': section_id,
            'filepath': os.path.join(INPUT_FOLDER, filename)
        })

# Ordenar por video_id e section_id
files_data.sort(key=lambda x: (x['video_id'], x['section_id']))

print(f"Encontrados {len(files_data)} arquivos para processar\n")

# Agrupar por vídeo para compilação
videos_content = defaultdict(list)

# Processar cada arquivo
for file_info in files_data:
    filename = file_info['filename']
    filepath = file_info['filepath']
    video_id = file_info['video_id']
    
    # Ler conteúdo
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read().strip()
    
    # Adicionar ao conteúdo do vídeo
    videos_content[video_id].append(text)
    
    # Gerar áudio com Polly
    print(f"Gerando áudio para {filename}...")
    response = polly_client.synthesize_speech(
        Text=text,
        OutputFormat=OUTPUT_FORMAT,
        VoiceId=VOICE_ID,
        LanguageCode=LANGUAGE_CODE,
        Engine=ENGINE
    )
    
    # Salvar áudio
    output_audio = os.path.join(OUTPUT_FOLDER, f"{Path(filename).stem}.mp3")
    with open(output_audio, 'wb') as f:
        f.write(response['AudioStream'].read())
    
    print(f"[OK] Áudio salvo: {output_audio}")

# Gerar arquivos de texto compilados por vídeo
print("\n=== Gerando compilações de texto ===")
for video_id in sorted(videos_content.keys()):
    compiled_text = '\n\n'.join(videos_content[video_id])
    output_txt = os.path.join(OUTPUT_FOLDER, f"v{video_id:02d}_compiled.txt")
    
    with open(output_txt, 'w', encoding='utf-8') as f:
        f.write(compiled_text)
    
    print(f"[OK] Compilação salva: {output_txt}")

print("\n=== Processamento concluído ===")
