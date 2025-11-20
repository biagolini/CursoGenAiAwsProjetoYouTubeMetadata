try:
    import os
    import json
    import datetime
    from datetime import timezone
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
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
DEFAULT_LANGUAGE = os.getenv('YOUTUBE_DEFAULT_LANGUAGE')

# Constantes do .env
DATA_FOLDER = os.getenv('DATA_FOLDER')
OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER')

METADATA_FILE = os.getenv('METADATA_OUTPUT_FILE')

def limpar_conteudo(titulo, descricao, video_id):
    """Limpa título e descrição para atender limites do YouTube"""
    titulo_limpo = titulo
    descricao_limpa = descricao
    
    # Limpar título (máximo 100 caracteres)
    if len(titulo) > 100:
        titulo_limpo = titulo[:100]
        print(f"[AVISO] Título truncado para vídeo {video_id}: {len(titulo)} -> 100 caracteres")
    
    # Limpar descrição (máximo 5000 caracteres, cortando no último ". ")
    if len(descricao) > 5000:
        descricao_temp = descricao
        while len(descricao_temp) > 5000:
            last_sentence_end = descricao_temp.rfind(". ", 0, 5000)
            if last_sentence_end == -1:
                descricao_temp = descricao_temp[:5000].rstrip()
                break
            else:
                descricao_temp = descricao_temp[:last_sentence_end + 2]
        
        descricao_limpa = descricao_temp
        print(f"[AVISO] Descrição truncada para vídeo {video_id}: {len(descricao)} -> {len(descricao_limpa)} caracteres")
    
    return titulo_limpo, descricao_limpa

def setup_youtube_client():
    """Configura cliente YouTube Data API"""
    TOKEN_FILE = "token_admin.json"
    
    try:
        if os.path.exists(TOKEN_FILE):
            try:
                # Tenta usar token existente
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, scopes=SCOPES)
                return googleapiclient.discovery.build("youtube", "v3", credentials=creds)
            except Exception as e:
                print(f"Token invalido ({e}), gerando novo...")
                os.remove(TOKEN_FILE)
        
        # Gera novo token apenas se necessário
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            "client_secret.json", SCOPES)
        creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
        
        return googleapiclient.discovery.build("youtube", "v3", credentials=creds)
        
    except Exception as e:
        print("ERRO: Falha na autenticacao com a API do YouTube")
        print(f"Detalhes: {str(e)}")
        print("\nSolucoes possiveis:")
        print("1. Verifique se o arquivo 'client_secret.json' existe no diretorio atual")
        print("2. Se o erro for relacionado a token invalido, delete o arquivo 'token_admin.json' e execute novamente")
        print("3. Verifique se as credenciais do Google Cloud Console estao configuradas corretamente")
        print("4. Confirme se a YouTube Data API v3 esta habilitada no seu projeto")
        print("5. Verifique se sua conta tem permissoes para modificar videos do canal")
        exit(1)

def load_generated_metadata():
    """Carrega metadados gerados pelo script 03"""
    if not os.path.exists(METADATA_FILE):
        print(f"Arquivo não encontrado: {METADATA_FILE}")
        print("Execute 06_metadata_generator.py primeiro")
        return {}
    
    with open(METADATA_FILE, "r", encoding="utf-8") as file:
        content = file.read().strip()
        if not content:
            print(f"Arquivo vazio: {METADATA_FILE}")
            print("Execute 06_metadata_generator.py para gerar metadados")
            return {}
        return json.loads(content)

def is_future_date(date_str):
    """Verifica se a data é futura"""
    try:
        scheduled_date_str = date_str.replace("Z", "+00:00")
        scheduled_date = datetime.datetime.fromisoformat(scheduled_date_str)
        current_date = datetime.datetime.now(timezone.utc)
        return scheduled_date > current_date
    except ValueError:
        print(f"Formato de data inválido: {date_str}")
        return False

def update_video_metadata(youtube, video_id, metadata):
    """Atualiza metadados de um vídeo no YouTube"""
    
    print(f"Atualizando vídeo: {video_id}")
    
    try:
        # Busca dados atuais do vídeo
        video_request = youtube.videos().list(
            part="snippet,localizations,status",
            id=video_id
        )
        video_response = video_request.execute()
        
        if not video_response["items"]:
            print(f"  Vídeo não encontrado: {video_id}")
            return False
        
        print(f"  Vídeo encontrado")
        
        # Obtém snippet atual
        current_snippet = video_response["items"][0]["snippet"]
        current_default_language = current_snippet.get("defaultLanguage")
        
        # Define idioma padrão baseado na configuração
        if DEFAULT_LANGUAGE:
            default_language = DEFAULT_LANGUAGE
            print(f"  Usando idioma configurado: {default_language}")
        elif current_default_language:
            default_language = current_default_language
            print(f"  Usando idioma existente do YouTube: {default_language}")
        else:
            default_language = "pt"
            print(f"  Usando idioma padrão (fallback): {default_language}")
        
        # Verifica se tem localizations
        if "localizations" not in metadata or default_language not in metadata["localizations"]:
            print(f"  [ERRO] Localização '{default_language}' não encontrada nos metadados")
            return False
        
        # Obtém conteúdo do idioma padrão
        default_content = metadata["localizations"][default_language]
        
        # Prepara snippet com conteúdo do idioma padrão
        # Aplicar limpeza no conteúdo padrão
        titulo_limpo, descricao_limpa = limpar_conteudo(
            default_content["title"], 
            default_content["description"], 
            video_id
        )
        
        snippet = {
            "title": titulo_limpo,
            "description": descricao_limpa,
            "tags": metadata.get("tags", []),
            "defaultLanguage": default_language,
            "categoryId": "27"
        }
        
        print(f"  Título: {snippet['title'][:50]}...")
        
        # Prepara localizações (todos os idiomas exceto o default)
        localizations = {}
        for lang, content in metadata["localizations"].items():
            if lang != default_language:
                titulo_limpo, descricao_limpa = limpar_conteudo(
                    content["title"], 
                    content["description"], 
                    video_id
                )
                localizations[lang] = {
                    "title": titulo_limpo,
                    "description": descricao_limpa
                }
        
        if localizations:
            print(f"  Localizações: {len(localizations)} idiomas")
        
        # Prepara body da requisição
        body = {
            "id": video_id,
            "snippet": snippet
        }
        
        if localizations:
            body["localizations"] = localizations
        
        # Atualiza status (agendamento)
        parts = ["snippet"]
        if localizations:
            parts.append("localizations")
        
        if "scheduledPublishTime" in metadata:
            scheduled_time = metadata["scheduledPublishTime"]
            if is_future_date(scheduled_time):
                status = {
                    "privacyStatus": "private",
                    "publishAt": scheduled_time,
                    "selfDeclaredMadeForKids": False
                }
                body["status"] = status
                parts.append("status")
                print(f"  Agendado para: {scheduled_time}")
            else:
                print(f"  Data de agendamento não é futura, ignorando")
        
        # Aplica atualizações
        youtube.videos().update(
            part=",".join(parts),
            body=body
        ).execute()
        print(f"  Vídeo atualizado com sucesso")
        return True
            
    except googleapiclient.errors.HttpError as e:
        print(f"  Erro HTTP: {e}")
        return False
    except Exception as e:
        print(f"  Erro inesperado: {e}")
        return False

def main():
    print("=== Aplicação de Metadados no YouTube ===\n")
    
    # Carrega metadados gerados
    metadata_dict = load_generated_metadata()
    
    if not metadata_dict:
        print("\n[ERRO] Faltam metadados para atualizar no YouTube")
        return
    
    print(f"Metadados carregados: {len(metadata_dict)} vídeos\n")
    
    # Setup cliente YouTube
    print("Configurando cliente YouTube...")
    youtube = setup_youtube_client()
    print("[OK] Cliente configurado\n")
    
    # Processa cada vídeo
    success_count = 0
    total_videos = len(metadata_dict)
    
    for i, (video_id, metadata) in enumerate(metadata_dict.items(), 1):
        print(f"[{i}/{total_videos}] Processando vídeo: {video_id}")
        
        if update_video_metadata(youtube, video_id, metadata):
            success_count += 1
        
        print()  # Linha em branco para separar
    
    # Resultado final
    print("=== Processamento Concluído ===")
    print(f"Vídeos atualizados com sucesso: {success_count}/{total_videos}")
    
    if success_count == total_videos:
        print("[OK] Todos os vídeos foram atualizados!")
    elif success_count > 0:
        print("[AVISO] Alguns vídeos foram atualizados com sucesso")
    else:
        print("[ERRO] Nenhum vídeo foi atualizado")

if __name__ == "__main__":
    main()
