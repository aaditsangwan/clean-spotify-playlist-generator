from dotenv import load_dotenv
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")

os.environ['SPOTIPY_CLIENT_ID'] = client_id
os.environ['SPOTIPY_CLIENT_SECRET'] = client_secret
os.environ['SPOTIPY_REDIRECT_URI'] = 'http://localhost:8888/callback'

# Set up Spotify OAuth
scope = 'playlist-read-private playlist-modify-private'
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

def get_user_playlist():
    playlists = sp.current_user_playlists()
    print("Your playlists:")
    for i, playlist in enumerate(playlists['items']):
        print(f"{i+1}. {playlist['name']}")
    
    choice = int(input("Enter the number of the playlist you want to clean: ")) - 1
    return playlists['items'][choice]['id']

def filter_clean_tracks(tracks):
    clean_tracks = []
    for item in tracks:
        track = item['track']
        if not track['explicit']:
            clean_tracks.append(track)
    return clean_tracks

def create_clean_playlist(original_playlist_id, clean_tracks):
    original_playlist = sp.playlist(original_playlist_id)
    user_id = sp.me()['id']
    new_playlist_name = f"Clean version of {original_playlist['name']}"
    new_playlist = sp.user_playlist_create(user_id, new_playlist_name, public=False)
    
    track_uris = [track['uri'] for track in clean_tracks]
    sp.user_playlist_add_tracks(user_id, new_playlist['id'], track_uris)
    
    return new_playlist['id']

def create_clean_playlist_from_original():
    playlist_id = get_user_playlist()
    tracks = sp.playlist_tracks(playlist_id)['items']
    clean_tracks = filter_clean_tracks(tracks)
    new_playlist_id = create_clean_playlist(playlist_id, clean_tracks)
    return new_playlist_id

if __name__ == "__main__":
    print("Welcome to the Spotify Clean Playlist Creator!")
    new_playlist_id = create_clean_playlist_from_original()
    print(f"Clean playlist created successfully!")
    print(f"New playlist ID: {new_playlist_id}")