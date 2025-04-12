import os
import sys
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QProgressBar, QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import requests
import json
from dotenv import load_dotenv
from tqdm import tqdm
from ytmusicapi import YTMusic
from pytube import YouTube

# Cargar variables de entorno
load_dotenv()

class DownloadThread(QThread):
    progress_update = pyqtSignal(int, int)  # (current, total)
    status_update = pyqtSignal(str)
    download_complete = pyqtSignal(bool, str)  # (success, message)
    
    def __init__(self, playlist_url, parent=None):
        super().__init__(parent)
        self.playlist_url = playlist_url
        self.is_running = True
        
    def run(self):
        try:
            # Configurar credenciales de Spotify
            client_id = os.getenv('SPOTIFY_CLIENT_ID')
            client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
            
            if not client_id or not client_secret:
                self.download_complete.emit(False, "Error: No se encontraron las credenciales de Spotify. Verifica el archivo .env")
                return
            
            # Autenticar con Spotify
            client_credentials_manager = SpotifyClientCredentials(
                client_id=client_id, 
                client_secret=client_secret
            )
            sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
            
            # Extraer ID de la playlist desde la URL
            playlist_id = self.extract_playlist_id(self.playlist_url)
            if not playlist_id:
                self.download_complete.emit(False, "Error: URL de playlist inválida")
                return
            
            # Obtener información de la playlist
            self.status_update.emit("Obteniendo información de la playlist...")
            playlist = sp.playlist(playlist_id)
            playlist_name = playlist['name']
            
            # Crear carpeta para la playlist
            download_dir = os.path.join(os.path.expanduser("~"), "Downloads", "SpotifyPlaylists", playlist_name)
            os.makedirs(download_dir, exist_ok=True)
            
            # Obtener todas las canciones de la playlist
            tracks = []
            results = playlist['tracks']
            tracks.extend(results['items'])
            while results['next']:
                results = sp.next(results)
                tracks.extend(results['items'])
            
            total_tracks = len(tracks)
            self.status_update.emit(f"Encontradas {total_tracks} canciones en la playlist '{playlist_name}'")
            
            # Inicializar YTMusic para búsqueda
            ytmusic = YTMusic()
            
            # Descargar cada canción
            for i, item in enumerate(tracks):
                if not self.is_running:
                    self.download_complete.emit(False, "Descarga cancelada por el usuario")
                    return
                    
                track = item['track']
                artist = track['artists'][0]['name']
                song_name = track['name']
                search_query = f"{song_name} {artist}"
                
                self.status_update.emit(f"Buscando: {search_query}")
                
                # Buscar en YouTube Music
                search_results = ytmusic.search(search_query, filter="songs")
                if not search_results:
                    self.status_update.emit(f"No se encontró: {search_query}")
                    continue
                
                # Obtener el ID del video de YouTube
                video_id = search_results[0]['videoId']
                
                # Crear URL de YouTube
                youtube_url = f"https://www.youtube.com/watch?v={video_id}"
                
                # Descargar audio usando pytube
                try:
                    self.status_update.emit(f"Buscando y descargando: {song_name} - {artist}")
                    
                    # Configurar YouTube con opciones para evitar errores comunes
                    yt = YouTube(
                        youtube_url,
                        use_oauth=False,
                        allow_oauth_cache=False,
                        on_progress_callback=lambda stream, chunk, bytes_remaining: self.status_update.emit(
                            f"Descargando {song_name} - {artist}: {int((1 - bytes_remaining / stream.filesize) * 100)}%"
                        )
                    )
                    
                    # Verificar que se obtuvo correctamente el objeto YouTube
                    if not yt:
                        self.status_update.emit(f"Error: No se pudo obtener información del video para {song_name}")
                        self.progress_update.emit(i + 1, total_tracks)
                        continue
                    
                    # Obtener el stream de audio con la mejor calidad
                    audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
                    
                    # Verificar que se obtuvo un stream de audio
                    if not audio_stream:
                        self.status_update.emit(f"Error: No se encontró stream de audio para {song_name}")
                        self.progress_update.emit(i + 1, total_tracks)
                        continue
                    
                    # Limpiar el nombre del archivo para evitar caracteres problemáticos
                    file_name = f"{song_name} - {artist}"
                    for char in ['/', '\\', '"', '?', ':', '*', '<', '>', '|']:
                        file_name = file_name.replace(char, '_')
                    
                    # Descargar el archivo
                    self.status_update.emit(f"Descargando: {song_name} - {artist}")
                    
                    # Intentar descargar con manejo de errores mejorado
                    try:
                        # Crear un nombre de archivo único para evitar conflictos
                        safe_filename = f"{file_name}_{i}"
                        mp3_file_path = os.path.join(download_dir, f"{safe_filename}.mp3")
                        
                        # Si ya existe un archivo con ese nombre, eliminarlo
                        if os.path.exists(mp3_file_path):
                            os.remove(mp3_file_path)
                            
                        # Descargar el archivo directamente como MP3
                        self.status_update.emit(f"Descargando archivo: {file_name}")
                        
                        # Primero descargamos a un archivo temporal
                        temp_file = audio_stream.download(
                            output_path=download_dir,
                            filename=safe_filename
                        )
                        
                        # Verificar que el archivo se descargó correctamente
                        if not os.path.exists(temp_file) or os.path.getsize(temp_file) == 0:
                            raise Exception("El archivo descargado está vacío o no existe")
                        
                        self.status_update.emit(f"Archivo descargado como: {temp_file}")
                        
                        # Renombrar el archivo a .mp3 si no tiene ya la extensión
                        if not temp_file.endswith('.mp3'):
                            if os.path.exists(mp3_file_path):
                                os.remove(mp3_file_path)
                            
                            self.status_update.emit(f"Renombrando a: {mp3_file_path}")
                            os.rename(temp_file, mp3_file_path)
                            temp_file = mp3_file_path
                        
                        # Verificar que el archivo final existe
                        if os.path.exists(mp3_file_path) and os.path.getsize(mp3_file_path) > 0:
                            self.status_update.emit(f"✅ Descargado: {song_name} - {artist}")
                        else:
                            raise Exception("Error al guardar el archivo descargado")
                            
                    except Exception as e:
                        self.status_update.emit(f"❌ Error al descargar {song_name}: {str(e)}")
                        # Continuar con la siguiente canción pero actualizar el progreso
                    
                    self.progress_update.emit(i + 1, total_tracks)
                except Exception as e:
                    self.status_update.emit(f"Error al descargar {song_name}: {str(e)}")
            
            self.download_complete.emit(True, f"Descarga completada. Las canciones se guardaron en: {download_dir}")
            
        except Exception as e:
            self.download_complete.emit(False, f"Error: {str(e)}")
    
    def extract_playlist_id(self, url):
        # Patrones para diferentes formatos de URL de Spotify
        patterns = [
            r'spotify:playlist:([a-zA-Z0-9]+)',  # spotify:playlist:ID
            r'https://open\.spotify\.com/playlist/([a-zA-Z0-9]+)',  # https://open.spotify.com/playlist/ID
            r'https://open\.spotify\.com/playlist/([a-zA-Z0-9]+)\?',  # https://open.spotify.com/playlist/ID?si=...
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def stop(self):
        self.is_running = False

class SpotifyDownloaderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.download_thread = None
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle('Descargador de Playlists de Spotify')
        self.setGeometry(300, 300, 600, 300)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Título
        title_label = QLabel('Descargador de Playlists de Spotify')
        title_font = QFont('Arial', 16, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Descripción
        desc_label = QLabel('Ingresa el enlace de tu playlist de Spotify para descargar todas las canciones')
        desc_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(desc_label)
        
        # URL input
        url_layout = QHBoxLayout()
        url_label = QLabel('URL de la Playlist:')
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('https://open.spotify.com/playlist/...')
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        main_layout.addLayout(url_layout)
        
        # Botones
        button_layout = QHBoxLayout()
        self.download_btn = QPushButton('Descargar')
        self.download_btn.clicked.connect(self.start_download)
        self.cancel_btn = QPushButton('Cancelar')
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.cancel_btn.setEnabled(False)
        button_layout.addWidget(self.download_btn)
        button_layout.addWidget(self.cancel_btn)
        main_layout.addLayout(button_layout)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)
        
        # Etiqueta de estado
        self.status_label = QLabel('Listo para descargar')
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # Verificar credenciales
        self.check_credentials()
    
    def check_credentials(self):
        client_id = os.getenv('SPOTIFY_CLIENT_ID')
        client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        
        if client_id == 'tu_client_id_aqui' or client_secret == 'tu_client_secret_aqui' or not client_id or not client_secret:
            QMessageBox.warning(self, 'Configuración Requerida', 
                              'Necesitas configurar tus credenciales de Spotify API en el archivo .env\n'
                              '1. Ve a https://developer.spotify.com/dashboard/ y crea una aplicación\n'
                              '2. Copia el Client ID y Client Secret\n'
                              '3. Edita el archivo .env en la carpeta del programa')
    
    def start_download(self):
        playlist_url = self.url_input.text().strip()
        if not playlist_url:
            QMessageBox.warning(self, 'Error', 'Por favor ingresa una URL de playlist válida')
            return
        
        # Deshabilitar botón de descarga y habilitar cancelar
        self.download_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        
        # Iniciar hilo de descarga
        self.download_thread = DownloadThread(playlist_url)
        self.download_thread.progress_update.connect(self.update_progress)
        self.download_thread.status_update.connect(self.update_status)
        self.download_thread.download_complete.connect(self.download_finished)
        self.download_thread.start()
    
    def cancel_download(self):
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.stop()
            self.status_label.setText('Cancelando descarga...')
    
    def update_progress(self, current, total):
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
    
    def update_status(self, message):
        self.status_label.setText(message)
    
    def download_finished(self, success, message):
        # Restaurar estado de los botones
        self.download_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        # Mostrar mensaje
        self.status_label.setText(message)
        
        if success:
            QMessageBox.information(self, 'Descarga Completada', message)
        else:
            QMessageBox.warning(self, 'Error', message)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SpotifyDownloaderApp()
    window.show()
    sys.exit(app.exec_())