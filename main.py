from dotenv import load_dotenv
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
from spotipy.exceptions import SpotifyException

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

def find_clean_version(track):
    track_name = track['name']
    main_artist = track['artists'][0]['name']
    query = f"track:{track_name} artist:{main_artist}"
    
    if len(query) > 250:
        query = query[:250]  # Truncate if still too long
    
    try:
        results = sp.search(q=query, type='track', limit=50, market='US')
        
        for item in results['tracks']['items']:
            if item['name'].lower() == track_name.lower() and not item['explicit']:
                return item
        
        # If no exact match is found, try a more lenient search
        #for item in results['tracks']['items']:
        #   if item['name'].lower().startswith(track_name.lower()) and not item['explicit']:
        #      return item
    
    except SpotifyException as e:
        print(f"Error searching for clean version of {track_name}: {str(e)}")
    
    return None

def filter_clean_tracks(tracks):
    clean_tracks = []
    for item in tracks:
        track = item['track']
        if not track['explicit']:
            clean_tracks.append(track)
        else:
            clean_version = find_clean_version(track)
            if clean_version:
                clean_tracks.append(clean_version)
    return clean_tracks


def add_tracks_with_retry(user_id, playlist_id, track_batch, max_retries=5):
    for attempt in range(max_retries):
        try:
            sp.user_playlist_add_tracks(user_id, playlist_id, track_batch)
            return
        except SpotifyException as e:
            if e.http_status == 429:  # Too Many Requests
                retry_after = int(e.headers.get('Retry-After', 1))
                print(f"Rate limited. Retrying after {retry_after} seconds...")
                time.sleep(retry_after)
            else:
                raise
    print("Max retries reached. Failed to add tracks.")

def create_clean_playlist(original_playlist_id, clean_tracks):
    original_playlist = sp.playlist(original_playlist_id)
    user_id = sp.me()['id']
    new_playlist_name = f"Clean version of {original_playlist['name']}"
    new_playlist = sp.user_playlist_create(user_id, new_playlist_name, public=False)
    
    track_uris = [track['uri'] for track in clean_tracks]
    
    for i in range(0, len(track_uris), 100):
        batch = track_uris[i:i+100]
        add_tracks_with_retry(user_id, new_playlist['id'], batch)
    
    return new_playlist['id']

def get_all_playlist_tracks(playlist_id):
    tracks = []
    results = sp.playlist_tracks(playlist_id)
    tracks.extend(results['items'])
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    return tracks

def create_clean_playlist_from_original():
    playlist_id = get_user_playlist()
    tracks = get_all_playlist_tracks(playlist_id)
    clean_tracks = filter_clean_tracks(tracks)
    new_playlist_id = create_clean_playlist(playlist_id, clean_tracks)
    return new_playlist_id

if __name__ == "__main__":
    print("Welcome to the Spotify Clean Playlist Creator!")
    new_playlist_id = create_clean_playlist_from_original()
    print(f"Clean playlist created successfully!")
    print(f"New playlist ID: {new_playlist_id}")