import streamlit as st
from dotenv import load_dotenv
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
from spotipy.exceptions import SpotifyException

# Load environment variables
load_dotenv()

# Set page config
st.set_page_config(page_title="Spotify Clean Playlist Creator", page_icon="🎵", layout="wide")

# Custom CSS
st.markdown("""
<style>
    body {
        font-family: 'Circular Std', 'Helvetica', 'Arial', sans-serif;
    }
    .stButton>button {
        background-color: #1DB954;
        color: white;
        border-radius: 500px;
        padding: 10px 20px;
        font-weight: bold;
    }
    .stSlider .stSliderValue {
        color: #1DB954;
    }
    @media (max-width: 600px) {
        .stApp {
            padding: 1rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# Set up Spotify OAuth
@st.cache_resource
def get_spotify_client():
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    
    os.environ['SPOTIPY_CLIENT_ID'] = client_id
    os.environ['SPOTIPY_CLIENT_SECRET'] = client_secret
    os.environ['SPOTIPY_REDIRECT_URI'] = 'http://localhost:8501'
    
    scope = 'playlist-read-private playlist-modify-private'
    return spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

sp = get_spotify_client()

def get_user_playlists():
    playlists = sp.current_user_playlists()
    return {playlist['name']: playlist['id'] for playlist in playlists['items']}

def find_clean_version(track):
    track_name = track['name']
    main_artist = track['artists'][0]['name']
    query = f"track:{track_name} artist:{main_artist}"
    
    if len(query) > 250:
        query = query[:250]
    
    try:
        results = sp.search(q=query, type='track', limit=50, market='US')
        
        for item in results['tracks']['items']:
            if item['name'].lower() == track_name.lower() and not item['explicit']:
                return item
    
    except SpotifyException as e:
        st.error(f"Error searching for clean version of {track_name}: {str(e)}")
    
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
            if e.http_status == 429:
                retry_after = int(e.headers.get('Retry-After', 1))
                st.warning(f"Rate limited. Retrying after {retry_after} seconds...")
                time.sleep(retry_after)
            else:
                raise
    st.error("Max retries reached. Failed to add tracks.")

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

def main():
    # Sidebar
    with st.sidebar:
        st.image("https://storage.googleapis.com/pr-newsroom-wp/1/2018/11/Spotify_Logo_RGB_White.png", width=200)
        st.title("Navigation")
        st.write("Welcome to the Spotify Clean Playlist Creator!")

    # Main content
    st.markdown("<h1 style='color: #1DB954;'>Spotify Clean Playlist Creator</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("Select Playlist")
        playlists = get_user_playlists()
        selected_playlist = st.selectbox("Choose a playlist to clean:", list(playlists.keys()))
    
    with col2:
        st.header("Create Clean Playlist")
        if st.button("Create Clean Playlist"):
            with st.spinner("Creating clean playlist..."):
                playlist_id = playlists[selected_playlist]
                tracks = get_all_playlist_tracks(playlist_id)
                clean_tracks = filter_clean_tracks(tracks)
                new_playlist_id = create_clean_playlist(playlist_id, clean_tracks)
            
            st.success("Clean playlist created successfully!")
            st.write(f"New playlist ID: {new_playlist_id}")
            st.markdown(f"[Open in Spotify](https://open.spotify.com/playlist/{new_playlist_id})")

if __name__ == "__main__":
    main()
