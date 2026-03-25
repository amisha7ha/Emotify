# recommendspot.py
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import random
import cloud_database as db
import time
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ==========================================
# 1. SETUP SPOTIFY CREDENTIALS
# ==========================================
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SEARCH_LIMIT = 500

def get_spotify_client():
    """Initialize and return Spotify client with error handling"""
    try:
        auth_manager = SpotifyClientCredentials(
            client_id=SPOTIPY_CLIENT_ID,
            client_secret=SPOTIPY_CLIENT_SECRET
        )
        sp = spotipy.Spotify(auth_manager=auth_manager)
        # Test the connection
        sp.search(q='test', limit=1)
        print("✅ Spotify client connected")
        return sp
    except spotipy.exceptions.SpotifyException as e:
        if e.http_status == 401:
            print("\n" + "="*60)
            print("❌ SPOTIFY AUTHENTICATION FAILED!")
            print("="*60)
            print("Your Spotify credentials are invalid or expired.")
            print("\nTo fix this:")
            print("1. Go to https://developer.spotify.com/dashboard")
            print("2. Create a new app")
            print("3. Copy the Client ID and Client Secret")
            print("4. Update the credentials in this file")
            print("="*60)
        return None
    except Exception as e:
        print(f"❌ Spotify connection error: {e}")
        return None

# ==========================================
# 2. EMOTION TO SEARCH QUERIES
# ==========================================
EMOTION_SEARCH = {
    'happy': ['happy', 'joy', 'dance', 'upbeat', 'feel good', 'celebration'],
    'sad': ['sad', 'emotional', 'heartbreak', 'cry', 'lonely', 'melancholy'],
    'angry': ['angry', 'rock', 'metal', 'rage', 'intense', 'hard rock'],
    'neutral': ['chill', 'calm', 'relaxing', 'peaceful', 'ambient']
}

# Language-specific queries
LANGUAGE_QUERIES = {
    'hindi': ['hindi', 'bollywood', 'hindi pop'],
    'nepali': ['nepali', 'nepali songs'],
    'english': ['']
}

# Language distribution: 80% Hindi/Nepali, 20% English
LANGUAGE_DISTRIBUTION = {
    'hindi': 0.2,
    'nepali': 0.3,
    'english': 0.5
}

def select_languages(needed_count):
    """Select which languages to fetch based on distribution"""
    languages = []
    for _ in range(needed_count):
        rand = random.random()
        if rand < LANGUAGE_DISTRIBUTION['hindi']:
            languages.append('hindi')
        elif rand < LANGUAGE_DISTRIBUTION['hindi'] + LANGUAGE_DISTRIBUTION['nepali']:
            languages.append('nepali')
        else:
            languages.append('english')
    return languages

def fetch_songs_by_language(emotion, language, needed, excluded_songs, seen_ids):
    """Fetch songs for specific emotion and language"""
    sp = get_spotify_client()
    if not sp:
        return []
    
    # Get emotion keywords
    emotion_keywords = EMOTION_SEARCH.get(emotion, ['music'])
    random.shuffle(emotion_keywords)
    
    # Get language keywords
    lang_keywords = LANGUAGE_QUERIES.get(language, [''])
    random.shuffle(lang_keywords)
    
    tracks = []
    
    # Try different combinations
    for e_keyword in emotion_keywords[:2]:
        for l_keyword in lang_keywords[:2]:
            try:
                # Build search query
                if l_keyword and e_keyword:
                    query = f"{e_keyword} {l_keyword}"
                elif l_keyword:
                    query = l_keyword
                elif e_keyword:
                    query = e_keyword
                else:
                    query = "songs"
                
                print(f"  🔍 Searching {language}: '{query}'")
                
                # Random offset for variety (0-80)
                random_offset = random.randint(0, 80)
                
                results = sp.search(
                    q=query,
                    type='track',
                    limit=SEARCH_LIMIT,
                    offset=random_offset
                )
                
                if results and results['tracks'] and results['tracks']['items']:
                    for track in results['tracks']['items']:
                        track_id = track['id']
                        
                        # Skip if already seen or excluded
                        if track_id in seen_ids or track_id in excluded_songs:
                            continue
                        
                        # Check if track has feedback
                        score_data = db.get_song_score(track_id, emotion)
                        
                        # Skip if disliked
                        if score_data['dislikes'] > score_data['likes']:
                            seen_ids.add(track_id)
                            continue
                        
                        song_data = {
                            'track_id': track_id,
                            'title': track['name'],
                            'artist': track['artists'][0]['name'],
                            'album': track['album']['name'],
                            'url': track['external_urls']['spotify'],
                            'preview_url': track.get('preview_url'),
                            'album_cover': track['album']['images'][0]['url'] if track['album']['images'] else None,
                            'popularity': track.get('popularity', 0),
                            'language': language,
                            'likes': score_data['likes'],
                            'dislikes': score_data['dislikes'],
                            'score': score_data['score']
                        }
                        
                        tracks.append(song_data)
                        seen_ids.add(track_id)
                        
                        if len(tracks) >= needed:
                            break
                            
                time.sleep(0.1)
                
            except Exception as e:
                print(f"  ⚠️ Error: {e}")
                continue
            
            if len(tracks) >= needed:
                break
        
        if len(tracks) >= needed:
            break
    
    return tracks

def fetch_random_songs(emotion, needed=10):
    """Fetch random songs from Spotify based on emotion with language distribution"""
    sp = get_spotify_client()
    if not sp:
        return []
    
    # Get excluded songs (disliked ones)
    excluded_songs = db.get_excluded_songs(emotion)
    excluded_set = set(excluded_songs)
    print(f"🚫 Excluding {len(excluded_set)} disliked songs")
    
    # Get liked songs to prioritize
    liked_songs = db.get_top_scoring_songs(emotion, limit=3)
    liked_ids = {song['track_id'] for song in liked_songs}
    
    all_tracks = []
    seen_ids = set(excluded_set)
    
    # First, add liked songs (if any)
    for song in liked_songs:
        if song['track_id'] not in seen_ids:
            # Get updated score data
            score = db.get_song_score(song['track_id'], emotion)
            song['likes'] = score['likes']
            song['dislikes'] = score['dislikes']
            song['score'] = score['score']
            all_tracks.append(song)
            seen_ids.add(song['track_id'])
    
    # Calculate how many more songs we need
    remaining_needed = needed - len(all_tracks)
    
    if remaining_needed > 0:
        # Select languages based on distribution
        languages_needed = select_languages(remaining_needed * 2)
        print(f"🌐 Language distribution: {languages_needed.count('hindi')} Hindi, "
              f"{languages_needed.count('nepali')} Nepali, {languages_needed.count('english')} English")
        
        # Fetch songs for each language
        for language in set(languages_needed):
            lang_count = languages_needed.count(language)
            if lang_count > 0 and len(all_tracks) < needed:
                print(f"\n📀 Fetching {lang_count} {language.upper()} songs...")
                lang_tracks = fetch_songs_by_language(
                    emotion, language, lang_count * 2, excluded_set, seen_ids
                )
                all_tracks.extend(lang_tracks)
                print(f"  ✅ Got {len(lang_tracks)} {language} songs")
    
    # Shuffle for randomness
    random.shuffle(all_tracks)
    
    # Report final distribution
    hindi_count = sum(1 for s in all_tracks if s.get('language') == 'hindi')
    nepali_count = sum(1 for s in all_tracks if s.get('language') == 'nepali')
    english_count = sum(1 for s in all_tracks if s.get('language') == 'english')
    print(f"\n📈 Final distribution: Hindi: {hindi_count}, Nepali: {nepali_count}, English: {english_count}")
    
    return all_tracks

def get_recommendations_for_emotion(emotion, limit=5):
    """Get 5 random songs for the detected emotion with learning system"""
    
    print(f"\n{'='*60}")
    print(f"🎯 Getting {limit} random songs for {emotion.upper()} emotion")
    print(f"{'='*60}")
    
    # Validate emotion
    valid_emotions = ['happy', 'sad', 'angry', 'neutral']
    if emotion not in valid_emotions:
        emotion = 'neutral'
    
    # Test Spotify connection first
    sp = get_spotify_client()
    if not sp:
        print("❌ Cannot connect to Spotify. Check your credentials.")
        return []
    
    # Fetch random songs (get extra to ensure we have enough)
    songs = fetch_random_songs(emotion, needed=limit + 3)
    
    if not songs:
        print("⚠️ No songs found. Trying fallback search...")
        # Fallback: simple search
        keywords = EMOTION_SEARCH.get(emotion, ['music'])
        for keyword in keywords[:2]:
            try:
                results = sp.search(q=keyword, type='track', limit=limit * 2)
                for track in results['tracks']['items']:
                    score = db.get_song_score(track['id'], emotion)
                    if score['dislikes'] <= score['likes']:
                        songs.append({
                            'track_id': track['id'],
                            'title': track['name'],
                            'artist': track['artists'][0]['name'],
                            'album': track['album']['name'],
                            'url': track['external_urls']['spotify'],
                            'preview_url': track.get('preview_url'),
                            'album_cover': track['album']['images'][0]['url'] if track['album']['images'] else None,
                            'popularity': track.get('popularity', 0),
                            'likes': score['likes'],
                            'dislikes': score['dislikes'],
                            'score': score['score']
                        })
                        if len(songs) >= limit:
                            break
                if len(songs) >= limit:
                    break
            except Exception as e:
                print(f"⚠️ Fallback error: {e}")
                continue
    
    if not songs:
        print("❌ No songs found. Please check your internet connection.")
        return []
    
    # Select first 'limit' songs
    final_songs = songs[:limit]
    
    # Save new songs to database
    try:
        db.save_songs_to_db(final_songs, emotion)
        print(f"💾 Saved {len(final_songs)} songs to database")
    except Exception as e:
        print(f"⚠️ Error saving to database: {e}")
    
    print(f"\n✅ {len(final_songs)} RANDOM SONGS READY:")
    for i, song in enumerate(final_songs):
        like_status = "❤️" if song.get('likes', 0) > 0 else "🆕"
        lang_flag = "🇮🇳" if song.get('language') == 'hindi' else "🇳🇵" if song.get('language') == 'nepali' else "🇬🇧"
        print(f"  {i+1}. {lang_flag} {like_status} {song['title']} by {song['artist']}")
    
    return final_songs

def get_song_details(track_id, emotion):
    """Get song details including feedback"""
    try:
        score = db.get_song_score(track_id, emotion)
        return {
            'likes': score['likes'],
            'dislikes': score['dislikes'],
            'score': score['score']
        }
    except Exception as e:
        print(f"Error getting song details: {e}")
        return {'likes': 0, 'dislikes': 0, 'score': 0.5}