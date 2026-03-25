# test_spotify.py
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

SPOTIPY_CLIENT_ID = '6daaed9762d14f56856ee243e1a880d7'
SPOTIPY_CLIENT_SECRET = '5c2b05fe6bd94a4594b9d41d7fd694a6'

print("Testing Spotify Connection...")
print(f"Client ID: {SPOTIPY_CLIENT_ID[:8]}...")
print(f"Client Secret: {SPOTIPY_CLIENT_SECRET[:8]}...")

try:
    # Initialize client
    client_credentials_manager = SpotifyClientCredentials(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET
    )
    sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
    
    # Test search for each emotion
    emotions = ['happy', 'sad', 'angry', 'neutral']
    
    for emotion in emotions:
        print(f"\nSearching for '{emotion}' songs...")
        results = sp.search(q=emotion, type='track', limit=5)
        
        if results['tracks']['items']:
            print(f"✓ Found {len(results['tracks']['items'])} songs")
            for track in results['tracks']['items']:
                print(f"  - {track['name']} by {track['artists'][0]['name']}")
        else:
            print(f"✗ No songs found for '{emotion}'")
            
    print("\n✅ Spotify connection is working!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")