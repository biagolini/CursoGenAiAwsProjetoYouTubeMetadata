try:
    import os
    import re
    import pandas as pd
    import google_auth_oauthlib.flow
    import googleapiclient.discovery
    import googleapiclient.errors
    from google.oauth2.credentials import Credentials
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
OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER')
TABLE_NAME = os.getenv('YOUTUBE_VIDEOS_TABLE')
MATERIAL_SOURCE = os.getenv('YOUTUBE_MATERIAL_SOURCE', 'transcription')
TRANSCRIPTION_LANGUAGES = os.getenv('YOUTUBE_TRANSCRIPTION_LANGUAGES', 'pt,en,es').split(',')

# Validar MATERIAL_SOURCE
VALID_SOURCES = ['transcription', 'pdf_segment', 'pdf_summary']
if MATERIAL_SOURCE not in VALID_SOURCES:
    print(f"ERRO: YOUTUBE_MATERIAL_SOURCE inválido: '{MATERIAL_SOURCE}'")
    print(f"Valores válidos: {', '.join(VALID_SOURCES)}")
    exit(1)

print(f"=== Content Source Matcher ===")
print(f"Fonte de material: {MATERIAL_SOURCE}\n")

# Carregar tabela de vídeos
table_path = os.path.join(DATA_FOLDER, TABLE_NAME)
if not os.path.exists(table_path):
    print(f"Tabela não encontrada: {table_path}")
    print("Execute 05_videos_table.py primeiro")
    exit(1)

df = pd.read_csv(table_path)
print(f"Tabela carregada: {len(df)} vídeos\n")

def normalize_text(text):
    """Normaliza texto para matching (remove caracteres especiais)"""
    normalized = re.sub(r'[_\-\(\)\[\]\.]+', ' ', text)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized

def match_with_pdf_table(df, source_column):
    """Faz matching com tabela de PDFs"""
    segments_table_name = os.getenv('PDF_SEGMENTS_TABLE')
    segments_table_path = os.path.join(DATA_FOLDER, segments_table_name)
    
    if not os.path.exists(segments_table_path):
        print(f"ERRO: Tabela de PDFs não encontrada: {segments_table_path}")
        print("Execute 03_pdf_splitter.py primeiro")
        exit(1)
    
    pdf_df = pd.read_csv(segments_table_path)
    
    # Verificar se coluna existe
    if source_column not in pdf_df.columns:
        print(f"ERRO: Coluna '{source_column}' não encontrada na tabela de PDFs")
        print(f"Colunas disponíveis: {', '.join(pdf_df.columns)}")
        exit(1)
    
    matches_found = 0
    manual_review = []
    
    for i, video_row in df.iterrows():
        video_title_normalized = normalize_text(video_row['video_title'])
        match_found = False
        
        for _, pdf_row in pdf_df.iterrows():
            segment_name_normalized = normalize_text(pdf_row['segment_name'])
            
            if video_title_normalized == segment_name_normalized:
                if pd.notna(pdf_row.get(source_column, '')) and pdf_row.get(source_column, ''):
                    df.at[i, 'material_link'] = pdf_row[source_column]
                    matches_found += 1
                    match_found = True
                    break
        
        if not match_found:
            df.at[i, 'material_link'] = "ADICIONAR_NOME_ARQUIVO_MANUALMENTE"
            manual_review.append(video_row['video_title'])
    
    print(f"=== Matching de Títulos ===")
    print(f"Matches encontrados: {matches_found}/{len(df)}")
    print(f"Vídeos para revisão manual: {len(manual_review)}")
    
    if manual_review:
        print("\nVídeos que precisam de revisão manual:")
        for title in manual_review:
            print(f"  - {title}")
    
    return df

def fetch_youtube_transcriptions(df):
    """Busca transcrições do YouTube"""
    SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
    TOKEN_FILE = "token_admin.json"
    
    # Criar pasta de transcrições
    TRANSCRIPTION_FOLDER = os.path.join(OUTPUT_FOLDER, 'youtube_transcriptions')
    os.makedirs(TRANSCRIPTION_FOLDER, exist_ok=True)
    
    # Autenticação
    try:
        if os.path.exists(TOKEN_FILE):
            try:
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, scopes=SCOPES)
                youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
            except Exception as e:
                print(f"Token inválido ({e}), gerando novo...")
                os.remove(TOKEN_FILE)
                flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                    "client_secret.json", SCOPES)
                creds = flow.run_local_server(port=0)
                with open(TOKEN_FILE, "w") as token:
                    token.write(creds.to_json())
                youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                "client_secret.json", SCOPES)
            creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, "w") as token:
                token.write(creds.to_json())
            youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
    except Exception as e:
        print("ERRO: Falha na autenticação com a API do YouTube")
        print(f"Detalhes: {str(e)}")
        print("\nSoluções possíveis:")
        print("1. Verifique se o arquivo 'client_secret.json' existe no diretório atual")
        print("2. Se o erro for relacionado a token inválido, delete o arquivo 'token_admin.json' e execute novamente")
        print("3. Verifique se as credenciais do Google Cloud Console estão configuradas corretamente")
        print("4. Confirme se a YouTube Data API v3 está habilitada no seu projeto")
        exit(1)
    
    # Processar cada vídeo
    success_count = 0
    failed_videos = []
    
    for i, row in df.iterrows():
        video_id = row['video_id']
        video_title = row['video_title']
        
        print(f"[{i+1}/{len(df)}] {video_title}")
        print(f"  ID: {video_id}")
        
        transcription_file = os.path.join(TRANSCRIPTION_FOLDER, f"{video_id}.txt")
        
        # Verificar se já existe
        if os.path.exists(transcription_file):
            print(f"  Transcrição já existe, atualizando referência...")
            df.at[i, 'material_link'] = transcription_file
            success_count += 1
            continue
        
        try:
            # Listar legendas disponíveis
            captions_list = youtube.captions().list(
                part="snippet",
                videoId=video_id
            ).execute()
            
            if not captions_list.get("items"):
                print(f"  ✗ Nenhuma legenda disponível")
                df.at[i, 'material_link'] = "TRANSCRICAO_NAO_ENCONTRADA"
                failed_videos.append((video_title, "Nenhuma legenda disponível"))
                continue
            
            # Procurar legenda nos idiomas preferidos
            caption_id = None
            caption_lang = None
            
            for lang in TRANSCRIPTION_LANGUAGES:
                for item in captions_list["items"]:
                    if item["snippet"]["language"] == lang:
                        caption_id = item["id"]
                        caption_lang = lang
                        break
                if caption_id:
                    break
            
            # Se não encontrou nos idiomas preferidos, pega a primeira disponível
            if not caption_id:
                caption_id = captions_list["items"][0]["id"]
                caption_lang = captions_list["items"][0]["snippet"]["language"]
            
            print(f"  Baixando legenda em: {caption_lang}")
            
            # Baixar legenda em formato SRT
            caption_content = youtube.captions().download(
                id=caption_id,
                tfmt="srt"
            ).execute()
            
            # Converter para texto puro (remover timestamps e numeração)
            caption_text = caption_content.decode('utf-8') if isinstance(caption_content, bytes) else caption_content
            
            # Processar SRT para extrair apenas o texto
            lines = caption_text.split('\n')
            text_only = []
            
            for line in lines:
                line = line.strip()
                # Pular linhas vazias, números e timestamps
                if line and not line.isdigit() and '-->' not in line:
                    text_only.append(line)
            
            # Salvar transcrição em arquivo texto
            with open(transcription_file, 'w', encoding='utf-8') as f:
                f.write(f"# Transcrição: {video_title}\n")
                f.write(f"# Video ID: {video_id}\n")
                f.write(f"# Idioma: {caption_lang}\n\n")
                f.write(' '.join(text_only))
            
            # Atualizar referência na tabela
            df.at[i, 'material_link'] = transcription_file
            
            print(f"  ✓ Transcrição salva: {transcription_file}")
            success_count += 1
            
        except googleapiclient.errors.HttpError as e:
            error_reason = e.error_details[0]['reason'] if e.error_details else str(e)
            print(f"  ✗ Erro HTTP: {error_reason}")
            df.at[i, 'material_link'] = "ERRO_AO_BUSCAR_TRANSCRICAO"
            failed_videos.append((video_title, error_reason))
            
        except Exception as e:
            print(f"  ✗ Erro: {e}")
            df.at[i, 'material_link'] = "ERRO_AO_BUSCAR_TRANSCRICAO"
            failed_videos.append((video_title, str(e)))
        
        print()
    
    print("=== Processamento de Transcrições ===")
    print(f"Transcrições obtidas: {success_count}/{len(df)}")
    print(f"Falhas: {len(failed_videos)}")
    
    if failed_videos:
        print("\nVídeos com falha:")
        for title, reason in failed_videos:
            print(f"  - {title}")
            print(f"    Motivo: {reason}")
    
    return df

# Processar de acordo com a fonte escolhida
if MATERIAL_SOURCE == 'pdf_segment':
    df = match_with_pdf_table(df, 'segment_path')
elif MATERIAL_SOURCE == 'pdf_summary':
    df = match_with_pdf_table(df, 'summary_path')
elif MATERIAL_SOURCE == 'transcription':
    df = fetch_youtube_transcriptions(df)

# Salvar tabela atualizada
df.to_csv(table_path, index=False)

print(f"\n=== Processamento Concluído ===")
print(f"Tabela atualizada: {table_path}")
