import os
import logging
import time
import requests
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('download_log.txt'),
        logging.StreamHandler()
    ]
)

def extract_playlist_id(playlist_url):
    """Extraer ID de la playlist desde la URL."""
    if 'playlist/' in playlist_url:
        return playlist_url.split('playlist/')[1].split('?')[0]
    return None

def download_playlist(playlist_url):
    try:
        # Cargar variables de entorno
        load_dotenv()
        
        # Configurar credenciales de Spotify
        client_id = os.getenv('SPOTIFY_CLIENT_ID')
        client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            logging.error("No se encontraron las credenciales de Spotify. Verifica el archivo .env")
            return False
        
        # Autenticar con Spotify
        logging.info("Iniciando autenticación con Spotify...")
        client_credentials_manager = SpotifyClientCredentials(
            client_id=client_id, 
            client_secret=client_secret
        )
        sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        
        # Extraer ID de la playlist
        playlist_id = extract_playlist_id(playlist_url)
        if not playlist_id:
            logging.error("URL de playlist inválida")
            return False
        
        # Obtener información de la playlist
        logging.info("Obteniendo información de la playlist...")
        playlist = sp.playlist(playlist_id)
        playlist_name = playlist['name']
        
        # Crear directorio para la playlist
        download_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "TestDownloads", playlist_name)
        os.makedirs(download_dir, exist_ok=True)
        logging.info(f"Directorio de descarga: {download_dir}")
        
        # Obtener todas las canciones
        tracks = []
        results = playlist['tracks']
        tracks.extend(results['items'])
        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])
        
        total_tracks = len(tracks)
        logging.info(f"Encontradas {total_tracks} canciones en la playlist '{playlist_name}'")
        
        # Descargar cada canción
        for i, item in enumerate(tracks, 1):
            track = item['track']
            artist = track['artists'][0]['name']
            song_name = track['name']
            search_query = f"{song_name} {artist}"
            
            logging.info(f"[{i}/{total_tracks}] Procesando: {search_query}")
            
            try:
                # Configurar opciones de yt-dlp
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'outtmpl': os.path.join(download_dir, f"{song_name} - {artist}.%(ext)s"),
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,
                    'default_search': 'ytsearch',
                }

                # Preparar nombre de archivo
                file_name = f"{song_name} - {artist}"
                for char in ['/', '\\', '"', '?', ':', '*', '<', '>', '|']:
                    file_name = file_name.replace(char, '_')
                
                ydl_opts['outtmpl'] = os.path.join(download_dir, f"{file_name}.%(ext)s")

                # Intentar descargar con reintentos
                max_retries = 3
                retry_count = 0
                success = False

                while retry_count < max_retries and not success:
                    try:
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([search_query])
                            success = True
                            logging.info(f"✅ Descargado exitosamente: {file_name}")
                    except Exception as e:
                        retry_count += 1
                        if retry_count == max_retries:
                            raise Exception(f"Error después de {max_retries} intentos: {str(e)}")
                        logging.warning(f"Intento {retry_count}/{max_retries} falló, reintentando...")
                        time.sleep(3 * retry_count)  # Backoff exponencial
                
                # Verificar archivo descargado
                if os.path.exists(mp3_file_path) and os.path.getsize(mp3_file_path) > 1024:
                    logging.info(f"✅ Descargado exitosamente: {file_name}")
                else:
                    logging.error(f"❌ Error: Archivo no encontrado o demasiado pequeño: {file_name}")
                
            except Exception as e:
                logging.error(f"Error al procesar {song_name}: {str(e)}")
        
        logging.info(f"Proceso completado. Las canciones se guardaron en: {download_dir}")
        return True
        
    except Exception as e:
        logging.error(f"Error general: {str(e)}")
        return False

if __name__ == "__main__":
    # URL de ejemplo de la playlist
    playlist_url = "https://open.spotify.com/playlist/5LfowgQmu9AzhxunKzsNRx?si=067431e3ca6e4ca3"
    
    logging.info("Iniciando proceso de descarga...")
    success = download_playlist(playlist_url)
    
    if success:
        logging.info("Proceso completado exitosamente")
    else:
        logging.error("El proceso falló")