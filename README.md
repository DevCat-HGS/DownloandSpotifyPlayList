# Descargador de Playlists de Spotify

Esta aplicación permite a los usuarios descargar canciones de una playlist de Spotify. Simplemente ingresa el enlace de tu playlist y la aplicación descargará todas las canciones en una carpeta con el mismo nombre de la playlist.

## Características

- Interfaz gráfica fácil de usar
- Descarga canciones de playlists públicas de Spotify
- Crea automáticamente una carpeta con el nombre de la playlist
- Muestra el progreso de descarga en tiempo real

## Requisitos

- Python 3.7 o superior
- Credenciales de la API de Spotify (Client ID y Client Secret)

## Instalación

1. Clona este repositorio o descarga los archivos
2. Instala las dependencias:

```
pip install -r requirements.txt
```

3. Configura tus credenciales de Spotify:
   - Ve a [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
   - Crea una nueva aplicación
   - Copia el Client ID y Client Secret
   - Edita el archivo `.env` y reemplaza los valores de `SPOTIFY_CLIENT_ID` y `SPOTIFY_CLIENT_SECRET`

## Uso

1. Ejecuta la aplicación:

```
python app.py
```

2. Ingresa la URL de la playlist de Spotify que deseas descargar
3. Haz clic en "Descargar"
4. Las canciones se guardarán en una carpeta con el nombre de la playlist dentro de la carpeta "Downloads/SpotifyPlaylists" en tu directorio de usuario

## Notas

- La aplicación utiliza YouTube como fuente para descargar las canciones
- La calidad del audio dependerá de la disponibilidad en YouTube
- Asegúrate de tener una conexión a Internet estable durante la descarga

## Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.