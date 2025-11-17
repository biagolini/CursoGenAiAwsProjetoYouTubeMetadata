try:
    import os
    import google_auth_oauthlib.flow
    import googleapiclient.discovery
    import pandas as pd
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

# Configuração do .env
MAX_VIDEOS = int(os.getenv('YOUTUBE_MAX_VIDEOS', 30))
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

# Constantes do .env
DATA_FOLDER = os.getenv('DATA_FOLDER')
TABLE_NAME = os.getenv('YOUTUBE_VIDEOS_TABLE')

# Autenticação
TOKEN_FILE = "token_readonly.json"

try:
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, scopes=SCOPES)
    else:
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            "client_secret.json", SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
except Exception as e:
    print("ERRO: Falha na autenticacao com a API do YouTube")
    print(f"Detalhes: {str(e)}")
    print("\nSolucoes possiveis:")
    print("1. Verifique se o arquivo 'client_secret.json' existe no diretorio atual")
    print("2. Se o erro for relacionado a token invalido, delete o arquivo 'token_readonly.json' e execute novamente")
    print("3. Verifique se as credenciais do Google Cloud Console estao configuradas corretamente")
    print("4. Confirme se a YouTube Data API v3 esta habilitada no seu projeto")
    exit(1)

# Obter playlist de uploads
channel_request = youtube.channels().list(part="contentDetails", mine=True)
channel_response = channel_request.execute()
uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

# Obter vídeos recentes
videos_request = youtube.playlistItems().list(
    part="snippet",
    playlistId=uploads_playlist_id,
    maxResults=MAX_VIDEOS
)
videos_response = videos_request.execute()

# Preparar dados para DataFrame
videos_data = []
for item in videos_response["items"]:
    video_id = item["snippet"]["resourceId"]["videoId"]
    video_title = item["snippet"]["title"]
    videos_data.append({
        "video_id": video_id,
        "video_title": video_title,
        "material_link": "",
        "bibliography_references": ""
    })

# Criar DataFrame e ordenar por título
df = pd.DataFrame(videos_data)
df = df.sort_values('video_title').reset_index(drop=True)

# Salvar CSV
os.makedirs(DATA_FOLDER, exist_ok=True)
csv_path = os.path.join(DATA_FOLDER, TABLE_NAME)
df.to_csv(csv_path, index=False)

print(f"CSV salvo em: {csv_path}")
print(f"Total de vídeos: {len(df)}")
