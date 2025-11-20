try:
    import os
    import json
    import boto3
    import pandas as pd
    from datetime import datetime, timedelta
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

PROMPT_ARN = os.getenv('BEDROCK_METADATA_GENERATOR_PROMPT_ARN')
OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER')
OUTPUT_FILE = os.getenv('METADATA_OUTPUT_FILE')
MATERIAL_LINK_SOURCE = os.getenv('YOUTUBE_MATERIAL_LINK_SOURCE', 'summary_path')

START_DATE = os.getenv('METADATA_START_DATE')
INTERVAL_DAYS = int(os.getenv('METADATA_INTERVAL_DAYS', 1))
PUBLISH_TIME = os.getenv('METADATA_PUBLISH_TIME')

METADATA_MAX_RETRIES = int(os.getenv('METADATA_MAX_RETRIES', 3))

# Metadados genéricos de fallback
FALLBACK_METADATA = {
    "localizations": {
        "pt": {
            "title": "Aprenda AWS: Guia Prático",
            "description": "Descubra como usar os serviços da AWS de forma prática e eficiente. Este vídeo apresenta conceitos fundamentais e exemplos reais para acelerar seu aprendizado em computação em nuvem.\n\n#AWS #Cloud #Tutorial #Tecnologia #Desenvolvimento"
        },
        "en": {
            "title": "Learn AWS: Practical Guide", 
            "description": "Discover how to use AWS services in a practical and efficient way. This video presents fundamental concepts and real examples to accelerate your cloud computing learning.\n\n#AWS #Cloud #Tutorial #Technology #Development"
        },
        "es": {
            "title": "Aprende AWS: Guía Práctica",
            "description": "Descubre cómo usar los servicios de AWS de manera práctica y eficiente. Este video presenta conceptos fundamentales y ejemplos reales para acelerar tu aprendizaje en computación en la nube.\n\n#AWS #Cloud #Tutorial #Tecnología #Desarrollo"
        }
    },
    "tags": ["AWS", "Cloud", "Tutorial", "Technology", "Development"]
}

REFERENCE_TEXT = {
    "pt": "Referências:",
    "es": "Referencias:",
    "en": "References:"
}

ADDITIONAL_LINKS = [
    { 
        "pt": "Conheça meu outro canal de tutoriais (em português) em: ",
        "es": "Conozca mi otro canal de Tutoriales (en portugues) en: ",
        "en": "Check out my other tutorial channel (in portuguese) at: ",
        "link": "https://www.youtube.com/@BiagoliniTech"
    },
    {
        "pt": "Leia mais artigos em ", 
        "es": "Lea más artículos en ",
        "en": "Read more articles at ",
        "link": "https://medium.com/@biagolini"
    }
]

# Define paths de tabelas
segments_table_name = os.getenv('PDF_SEGMENTS_TABLE')
youtube_table_name = os.getenv('YOUTUBE_VIDEOS_TABLE')

segments_table_path = os.path.join(DATA_FOLDER, segments_table_name)
youtube_table_path = os.path.join(DATA_FOLDER, youtube_table_name)

# Configuração com timeout maior para PDFs grandes
bedrock_config = Config(
    read_timeout=600,  # 10 minutos
    connect_timeout=60,
    retries={'max_attempts': 3, 'mode': 'adaptive'}
)

# Inicializar clientes AWS
bedrock_runtime_client = boto3.client("bedrock-runtime", config=bedrock_config)

def load_video_data():
    """Carrega dados dos vídeos do CSV"""
    df = pd.read_csv(youtube_table_path)
    original_count = len(df)
    
    # Filtrar apenas vídeos com material_link preenchido
    df_filtered = df[df['material_link'] != "ADICIONAR_NOME_ARQUIVO_MANUALMENTE"].copy()
    
    # Filtrar apenas vídeos cujo arquivo existe
    df_filtered = df_filtered[df_filtered['material_link'].apply(os.path.exists)].copy()
    
    # Preencher valores NaN em bibliography_references com string vazia
    df_filtered['bibliography_references'] = df_filtered['bibliography_references'].fillna('')
    
    return df_filtered, original_count

def load_transcription_if_exists(video_id):
    """Carrega transcrição se existir arquivo correspondente"""
    transcription_folder = os.path.join(OUTPUT_FOLDER, "transcriptions")
    transcription_file = os.path.join(transcription_folder, f"{video_id}.txt")
    
    if os.path.exists(transcription_file):
        try:
            with open(transcription_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    print(f"  Transcrição encontrada: {len(content)} caracteres")
                    return content
        except Exception as e:
            print(f"  Erro ao ler transcrição: {e}")
    
    return None

def sanitize_document_name(file_path):
    """Sanitiza o nome do documento para atender requisitos do Bedrock"""
    file_extension = os.path.splitext(file_path)[1][1:].lower()
    document_name = os.path.basename(file_path).replace(f".{file_extension}", "")
    
    # Remover caracteres não permitidos (manter apenas alfanuméricos, espaços, hífens, parênteses e colchetes)
    import re
    document_name = re.sub(r'[^a-zA-Z0-9\s\-\(\)\[\]]', '-', document_name)
    
    # Substituir múltiplos espaços consecutivos por um único espaço
    document_name = re.sub(r'\s+', ' ', document_name)
    
    # Substituir múltiplos hífens consecutivos por um único hífen
    document_name = re.sub(r'-+', '-', document_name)
    
    # Remover espaços e hífens no início e fim
    document_name = document_name.strip(' -')
    
    return document_name



def truncate_description(description, max_length=5000):
    """Trunca descrição se exceder o limite, cortando no último '. ' (ponto + espaço)"""
    if len(description) <= max_length:
        return description
    
    # Cortar até caber no limite
    while len(description) > max_length:
        # Encontrar a última ocorrência de ". " antes do limite
        last_sentence_end = description.rfind(". ", 0, max_length)
        
        if last_sentence_end == -1:
            # Se não encontrar ". ", cortar no limite mesmo
            description = description[:max_length].rstrip()
            break
        else:
            # Cortar após o ". " (incluindo o ponto e espaço)
            description = description[:last_sentence_end + 2]
    
    return description

def add_references_and_links(metadata, bibliography_references):
    """Adiciona referências bibliográficas e links adicionais aos metadados"""
    
    # Processar referências bibliográficas
    references_text = {}
    if bibliography_references and bibliography_references.strip():
        reference_links = bibliography_references.strip().split()
        if reference_links:
            for lang in ["pt", "es", "en"]:
                ref_text = f"\n\n{REFERENCE_TEXT[lang]}\n"
                for link in reference_links:
                    ref_text += f"- {link}\n"
                references_text[lang] = ref_text.rstrip()
    
    # Processar links adicionais
    additional_text = {}
    for lang in ["pt", "es", "en"]:
        add_text = "\n\n"
        for item in ADDITIONAL_LINKS:
            add_text += f"{item[lang]}{item['link']}\n"
        additional_text[lang] = add_text.rstrip()
    
    # Aplicar às localizações
    if "localizations" in metadata:
        for lang in metadata["localizations"]:
            if lang in references_text:
                metadata["localizations"][lang]["description"] += references_text[lang]
            if lang in additional_text:
                metadata["localizations"][lang]["description"] += additional_text[lang]
            
            # Truncar descrição se exceder 5000 caracteres
            original_length = len(metadata["localizations"][lang]["description"])
            metadata["localizations"][lang]["description"] = truncate_description(
                metadata["localizations"][lang]["description"]
            )
            new_length = len(metadata["localizations"][lang]["description"])
            
            if original_length > new_length:
                print(f"  Descrição {lang} truncada: {original_length} → {new_length} caracteres")
    
    return metadata

def validate_metadata(result):
    """Valida se os metadados têm localizations obrigatórias"""
    if not result:
        return False, "Resultado vazio"
    
    if "localizations" not in result:
        return False, "Campo 'localizations' ausente"
    
    localizations = result["localizations"]
    
    # Verifica se tem pelo menos português
    if "pt" not in localizations:
        return False, "Localização 'pt' ausente"
    
    pt = localizations["pt"]
    if not pt.get("title"):
        return False, "Campo 'title' ausente ou vazio em 'pt'"
    
    if not pt.get("description"):
        return False, "Campo 'description' ausente ou vazio em 'pt'"
    
    return True, "Válido"

def generate_metadata_with_bedrock(file_path, call_number, transcription_content=None):
    """Gera metadados usando AWS Bedrock com Tool Use"""
    
    print(f"Gerando metadados...")
    print(f"Arquivo: {file_path}")
    
    if transcription_content:
        # Modo transcrição: apenas texto, sem anexar arquivo
        print(f"Transcrição incluída: {len(transcription_content)} caracteres")
        
        transcription_text = f"the following transcription context:\n\nThe following context is the transcription of the audio content. Please note that there may be errors due to transcription inaccuracies:\n\n<AUDIO-TRANSCRIPTION>\n{transcription_content}\n</AUDIO-TRANSCRIPTION>"
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"text": f"Generate YouTube metadata from {transcription_text}."}
                ]
            }
        ]
    else:
        # Modo documento: anexar arquivo
        with open(file_path, "rb") as f:
            doc_bytes = f.read()
        
        file_extension = os.path.splitext(file_path)[1][1:].lower()
        document_name = sanitize_document_name(file_path)
        
        print(f"Documento: {len(doc_bytes)} bytes ({len(doc_bytes) / 1024 / 1024:.2f} MB)")
        
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
                    {"text": "Generate YouTube metadata from the attached document."}
                ]
            }
        ]
    
    # Tentar até METADATA_MAX_RETRIES vezes
    for attempt in range(1, METADATA_MAX_RETRIES + 1):
        if attempt > 1:
            print(f"Tentativa {attempt}/{METADATA_MAX_RETRIES}...")
        else:
            print(f"Enviando requisição para Bedrock...")
        
        try:
            response = bedrock_runtime_client.converse(
                modelId=PROMPT_ARN,
                messages=messages
            )
            
            # Extrair resultado do Tool Use
            result = response["output"]["message"]["content"][0]["toolUse"]["input"]
            
            # Validar metadados
            is_valid, validation_message = validate_metadata(result)
            
            if is_valid:
                print(f"  Metadados gerados com sucesso")
                return result
            else:
                print(f"  [AVISO] Metadados incompletos: {validation_message}")
                if attempt < METADATA_MAX_RETRIES:
                    print(f"Tentando novamente...")
                else:
                    print(f"  [AVISO] Máximo de tentativas atingido, usando metadados genéricos")
                    return FALLBACK_METADATA.copy()
        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            print(f"  Erro: {error_code}")
            print(f"  Mensagem: {error_message}")
            
            if attempt < METADATA_MAX_RETRIES:
                print(f"  Tentando novamente ({attempt + 1}/{METADATA_MAX_RETRIES})...")
            else:
                print(f"  [AVISO] Máximo de tentativas atingido, usando metadados genéricos")
                print("  Sugestões para resolver o problema:")
                
                if error_code == "ModelErrorException":
                    print("  - Verifique se o limite máximo de tokens de saída no prompt está suficiente (recomendado: 500+)")
                    print("  - Verifique se o limite máximo de tokens de entrada suporta o tamanho do documento")
                    print("  - Arquivos muito grandes podem exceder o limite de entrada do modelo")
                    print("  - Confirme que o schema da ferramenta está configurado corretamente no Bedrock Prompt Manager")
                    print("  - Verifique se o ARN do prompt é válido e acessível")
                elif error_code == "ValidationException":
                    print("  - O nome do arquivo contém caracteres inválidos ou múltiplos espaços consecutivos")
                    print("  - Renomeie o arquivo usando apenas: letras, números, espaços, hífens, parênteses e colchetes")
                elif error_code == "ThrottlingException":
                    print("  - Muitas requisições simultâneas. Aguarde alguns segundos e tente novamente")
                else:
                    print("  - Verifique as configurações do modelo no Bedrock")
                
                print(f"  - Consulte mais informações sobre o modelo em:")
                print(f"    https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html")
                
                return FALLBACK_METADATA.copy()
        
        except Exception as e:
            print(f"  Erro inesperado: {e}")
            if attempt < METADATA_MAX_RETRIES:
                print(f"  Tentando novamente ({attempt + 1}/{METADATA_MAX_RETRIES})...")
            else:
                print(f"  [AVISO] Máximo de tentativas atingido, usando metadados genéricos")
                return FALLBACK_METADATA.copy()
    
    return FALLBACK_METADATA.copy()

# Carregar vídeos
df, original_count = load_video_data()

# Estatísticas de filtragem
if original_count == len(df):
    print(f"Tabela carregada com {original_count} vídeos, todos com arquivos válidos para processamento.\n")
else:
    print(f"Tabela original: {original_count} vídeos")
    print(f"Após filtrar vídeos sem referência ou com arquivos inexistentes: {len(df)} vídeos para processamento.\n")

if df.empty:
    print("Nenhum vídeo encontrado com material_link válido e arquivo existente.")
    exit(1)

# Carregar metadados existentes
existing_metadata = {}
if os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if content:
            existing_metadata = json.loads(content)
        else:
            # Arquivo vazio, sobrescrever com {}
            with open(OUTPUT_FILE, "w", encoding="utf-8") as fw:
                json.dump({}, fw)
    print(f"Metadados existentes: {len(existing_metadata)} vídeos\n")

# Processar cada vídeo
success_count = 0
start_date = datetime.strptime(START_DATE, "%Y-%m-%d")

for i, (_, row) in enumerate(df.iterrows(), 1):
    print(f"\n[{i}/{len(df)}] Processando: {row['material_link']}")
    
    video_id = row["video_id"]
    
    # Verificar se já foi processado
    if video_id in existing_metadata:
        print(f"  Vídeo já processado, pulando...")
        continue
    
    # Verificar se arquivo existe
    if not os.path.exists(row["material_link"]):
        print(f"  Arquivo não encontrado: {row['material_link']}")
        continue
    
    # Carregar transcrição se existir
    transcription_content = load_transcription_if_exists(video_id)
    
    # Gerar metadados
    new_metadata = generate_metadata_with_bedrock(
        row["material_link"],
        i,
        transcription_content
    )
    
    # Adicionar referências e links adicionais
    new_metadata = add_references_and_links(new_metadata, row["bibliography_references"])
    
    # Calcular data de publicação
    scheduled_date = (start_date + timedelta(days=(i-1) * INTERVAL_DAYS)).strftime("%Y-%m-%d")
    new_metadata["scheduledPublishTime"] = f"{scheduled_date}{PUBLISH_TIME}"
    
    # Adicionar metadados com o video_id correto
    existing_metadata[video_id] = new_metadata
    success_count += 1
    
    # Salvar progresso
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_metadata, f, ensure_ascii=False, indent=2)

print(f"\n=== Processamento Concluído ===")
print(f"Vídeos processados: {success_count}/{len(df)}")
print(f"Metadados salvos em: {OUTPUT_FILE}")
print(f"Total de vídeos no arquivo: {len(existing_metadata)}")
