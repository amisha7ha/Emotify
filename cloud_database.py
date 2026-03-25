# cloud_database.py
import psycopg2
from datetime import datetime
import traceback

# Your Neon URL
NEON_URL = "postgresql://neondb_owner:npg_kAKN5SlJs1IE@ep-icy-cherry-a85u9or1-pooler.eastus2.azure.neon.tech/neondb?sslmode=require&channel_binding=require"

def get_connection():
    """Get Neon database connection"""
    try:
        conn = psycopg2.connect(NEON_URL)
        print("Database connected successfully")
        return conn
    except Exception as e:
        print(f"Connection failed: {e}")
        print(traceback.format_exc())
        return None

def init_database():
    """Create tables if they don't exist"""
    print("\nINITIALIZING DATABASE...")
    conn = get_connection()
    if not conn:
        return False
    
    cur = conn.cursor()
    
    try:
        # Drop existing tables to start fresh (comment this out after first run)
        print("Dropping existing tables...")
        cur.execute("DROP TABLE IF EXISTS user_feedback CASCADE;")
        cur.execute("DROP TABLE IF EXISTS song_scores CASCADE;")
        cur.execute("DROP TABLE IF EXISTS songs CASCADE;")
        
        # Create songs table
        cur.execute("""
            CREATE TABLE songs (
                song_id TEXT PRIMARY KEY,
                song_name TEXT NOT NULL,
                artist TEXT NOT NULL,
                album TEXT,
                emotion TEXT NOT NULL,
                spotify_url TEXT,
                preview_url TEXT,
                album_cover TEXT,
                popularity INTEGER,
                fetched_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print(" Songs table created")
        
        # Create feedback table
        cur.execute("""
            CREATE TABLE user_feedback (
                feedback_id SERIAL PRIMARY KEY,
                song_id TEXT REFERENCES songs(song_id) ON DELETE CASCADE,
                emotion TEXT NOT NULL,
                feedback_type TEXT NOT NULL,
                session_id TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(song_id, session_id)
            )
        """)
        print(" Feedback table created")
        
        # Create scores table
        cur.execute("""
            CREATE TABLE song_scores (
                song_id TEXT PRIMARY KEY REFERENCES songs(song_id) ON DELETE CASCADE,
                emotion TEXT NOT NULL,
                like_count INTEGER DEFAULT 0,
                dislike_count INTEGER DEFAULT 0,
                score FLOAT DEFAULT 0.5,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print(" Scores table created")
        
        # Create indexes for better performance
        cur.execute("CREATE INDEX IF NOT EXISTS idx_songs_emotion ON songs(emotion)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_feedback_song ON user_feedback(song_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_scores_emotion ON song_scores(emotion)")
        
        conn.commit()
        print("Database initialized successfully")
        return True
        
    except Exception as e:
        print(f"Error creating tables: {e}")
        print(traceback.format_exc())
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()

def save_songs_to_db(songs, emotion):
    """Save multiple songs to database"""
    print(f"\n SAVING SONGS FOR {emotion.upper()}")
    print(f"Received {len(songs)} songs to save")
    
    if not songs:
        print("⚠️ No songs to save")
        return 0
    
    conn = get_connection()
    if not conn:
        return 0
    
    cur = conn.cursor()
    saved_count = 0
    failed_count = 0
    
    try:
        for i, song in enumerate(songs):
            print(f"\n Processing song {i+1}:")
            print(f"  ID: {song['track_id']}")
            print(f"  Title: {song['title']}")
            print(f"  Artist: {song['artist']}")
            print(f"  Album: {song.get('album', 'Unknown')}")
            
            try:
                cur.execute("""
                    INSERT INTO songs 
                    (song_id, song_name, artist, album, emotion, spotify_url, 
                     preview_url, album_cover, popularity, fetched_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (song_id) DO NOTHING
                    RETURNING song_id
                """, (
                    song['track_id'], 
                    song['title'], 
                    song['artist'], 
                    song.get('album', 'Unknown Album'),
                    emotion, 
                    song['url'],
                    song.get('preview_url'), 
                    song.get('album_cover'), 
                    song.get('popularity', 0),
                    datetime.now()
                ))
                
                result = cur.fetchone()
                
                if result:
                    saved_count += 1
                    print("  NEW song saved successfully")
                else:
                    print("  Song already exists in database")
                    
            except Exception as e:
                failed_count += 1
                print(f"  Error saving song: {e}")
                continue
        
        conn.commit()
        print(f"\nSUMMARY: {saved_count} new songs saved, {failed_count} failed, {len(songs)-saved_count-failed_count} already existed")
        return saved_count
        
    except Exception as e:
        print(f" Error in save_songs_to_db: {e}")
        print(traceback.format_exc())
        conn.rollback()
        return 0
    finally:
        cur.close()
        conn.close()

def add_feedback(song_id, emotion, feedback_type, session_id):
    """Add user feedback and update scores"""
    print(f"\n ADDING FEEDBACK")
    print(f"  Song ID: {song_id[:8]}...")
    print(f"  Emotion: {emotion}")
    print(f"  Type: {feedback_type}")
    print(f"  Session: {session_id}")
    
    conn = get_connection()
    if not conn:
        return False
    
    cur = conn.cursor()
    
    try:
        # First check if song exists
        cur.execute("SELECT song_id, song_name FROM songs WHERE song_id = %s", (song_id,))
        song = cur.fetchone()
        
        if not song:
            print(f" Song {song_id} not found in database!")
            print("   Songs must be saved before adding feedback")
            return False
        
        print(f"   Found song: {song[1]}")
        
        # Insert feedback
        cur.execute("""
            INSERT INTO user_feedback (song_id, emotion, feedback_type, session_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (song_id, session_id) DO NOTHING
            RETURNING feedback_id
        """, (song_id, emotion, feedback_type, session_id))
        
        result = cur.fetchone()
        
        if result:
            print(f"   New feedback recorded with ID: {result[0]}")
            
            # Update scores
            cur.execute("""
                INSERT INTO song_scores (song_id, emotion, like_count, dislike_count, score)
                VALUES (%s, %s, 
                        CASE WHEN %s = 'like' THEN 1 ELSE 0 END,
                        CASE WHEN %s = 'dislike' THEN 1 ELSE 0 END,
                        CASE WHEN %s = 'like' THEN 0.8 ELSE 0.2 END)
                ON CONFLICT (song_id) DO UPDATE SET
                    like_count = song_scores.like_count + CASE WHEN %s = 'like' THEN 1 ELSE 0 END,
                    dislike_count = song_scores.dislike_count + CASE WHEN %s = 'dislike' THEN 1 ELSE 0 END,
                    score = (song_scores.like_count + 2.0) / (song_scores.like_count + song_scores.dislike_count + 4.0),
                    last_updated = CURRENT_TIMESTAMP
                RETURNING like_count, dislike_count, score
            """, (song_id, emotion, feedback_type, feedback_type, feedback_type, feedback_type, feedback_type))
            
            scores = cur.fetchone()
            print(f"   Updated scores - Likes: {scores[0]}, Dislikes: {scores[1]}, Score: {scores[2]:.3f}")
            
            conn.commit()
            return True
        else:
            print(f"  Info Feedback already exists for this song/session")
            conn.rollback()
            return False
            
    except Exception as e:
        print(f" Error adding feedback: {e}")
        print(traceback.format_exc())
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()

def get_excluded_songs(emotion):
    """Get song IDs that are disliked (dislikes > likes)"""
    print(f"\n GETTING EXCLUDED SONGS FOR {emotion.upper()}")
    conn = get_connection()
    if not conn:
        return []
    
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT song_id, like_count, dislike_count 
            FROM song_scores 
            WHERE emotion = %s AND dislike_count > like_count
        """, (emotion,))
        
        results = cur.fetchall()
        excluded = [row[0] for row in results]
        
        if excluded:
            print(f"  Found {len(excluded)} excluded songs:")
            for i, row in enumerate(results[:3]):  # Show first 3
                print(f"    {i+1}. ID: {row[0][:8]}... (likes: {row[1]}, dislikes: {row[2]})")
        else:
            print(f"  No excluded songs found for {emotion}")
            
        return excluded
    except Exception as e:
        print(f" Error getting excluded songs: {e}")
        return []
    finally:
        cur.close()
        conn.close()

def get_top_scoring_songs(emotion, limit=2):
    """Get top liked songs for an emotion"""
    print(f"\n GETTING TOP SONGS FOR {emotion.upper()}")
    conn = get_connection()
    if not conn:
        return []
    
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT s.song_id, s.song_name, s.artist, s.spotify_url, s.album_cover,
                   COALESCE(ss.like_count, 0) as likes,
                   COALESCE(ss.dislike_count, 0) as dislikes,
                   COALESCE(ss.score, 0.5) as score
            FROM songs s
            LEFT JOIN song_scores ss ON s.song_id = ss.song_id
            WHERE s.emotion = %s 
              AND (ss.like_count > ss.dislike_count OR ss.like_count IS NULL)
            ORDER BY ss.score DESC NULLS LAST, ss.like_count DESC
            LIMIT %s
        """, (emotion, limit))
        
        results = cur.fetchall()
        
        songs = []
        for row in results:
            song_data = {
                'track_id': row[0],
                'title': row[1],
                'artist': row[2],
                'url': row[3],
                'album_cover': row[4],
                'likes': row[5] or 0,
                'dislikes': row[6] or 0,
                'score': float(row[7]) if row[7] else 0.5
            }
            songs.append(song_data)
            print(f"  • {song_data['title']} by {song_data['artist']} (likes: {song_data['likes']}, score: {song_data['score']:.3f})")
        
        if not songs:
            print(f"  No liked songs found for {emotion}")
            
        return songs
    except Exception as e:
        print(f" Error getting top songs: {e}")
        return []
    finally:
        cur.close()
        conn.close()

def get_song_score(song_id, emotion):
    """Get score for a specific song"""
    conn = get_connection()
    if not conn:
        return {'likes': 0, 'dislikes': 0, 'score': 0.5}
    
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT like_count, dislike_count, score 
            FROM song_scores 
            WHERE song_id = %s
        """, (song_id,))
        
        result = cur.fetchone()
        
        if result:
            return {
                'likes': result[0] or 0,
                'dislikes': result[1] or 0,
                'score': float(result[2]) if result[2] else 0.5
            }
        return {'likes': 0, 'dislikes': 0, 'score': 0.5}
    except Exception as e:
        print(f" Error getting song score: {e}")
        return {'likes': 0, 'dislikes': 0, 'score': 0.5}
    finally:
        cur.close()
        conn.close()

def check_database():
    """Check what's in the database"""
    print("\n" + "="*60)
    print(" DATABASE STATUS REPORT")
    print("="*60)
    
    conn = get_connection()
    if not conn:
        return
    
    cur = conn.cursor()
    
    try:
        # Songs count
        cur.execute("SELECT COUNT(*) FROM songs")
        songs = cur.fetchone()[0]
        print(f" Total Songs: {songs}")
        
        if songs > 0:
            # Songs by emotion
            cur.execute("SELECT emotion, COUNT(*) FROM songs GROUP BY emotion ORDER BY emotion")
            print("\n Songs by Emotion:")
            for row in cur.fetchall():
                print(f"  • {row[0]}: {row[1]}")
            
            # Sample songs
            cur.execute("SELECT song_name, artist, emotion, fetched_date FROM songs ORDER BY fetched_date DESC LIMIT 5")
            print("\n Latest 5 Songs:")
            for row in cur.fetchall():
                print(f"  • {row[0]} by {row[1]} ({row[2]}) - {row[3].strftime('%Y-%m-%d %H:%M') if row[3] else 'Unknown'}")
        
        # Feedback count
        cur.execute("SELECT COUNT(*) FROM user_feedback")
        feedback = cur.fetchone()[0]
        print(f"\n Total Feedback Records: {feedback}")
        
        if feedback > 0:
            cur.execute("SELECT feedback_type, COUNT(*) FROM user_feedback GROUP BY feedback_type")
            print("  Feedback Breakdown:")
            for row in cur.fetchall():
                print(f"    • {row[0]}: {row[1]}")
            
            # Recent feedback
            cur.execute("""
                SELECT s.song_name, uf.feedback_type, uf.timestamp 
                FROM user_feedback uf
                JOIN songs s ON uf.song_id = s.song_id
                ORDER BY uf.timestamp DESC 
                LIMIT 5
            """)
            print("\n Recent Feedback:")
            for row in cur.fetchall():
                print(f"  • {row[0]}: {row[1]} ({row[2].strftime('%Y-%m-%d %H:%M') if row[2] else 'Unknown'})")
        
        # Scores count
        cur.execute("SELECT COUNT(*) FROM song_scores")
        scores = cur.fetchone()[0]
        print(f"\n Songs with Scores: {scores}")
        
        if scores > 0:
            # Top liked
            cur.execute("""
                SELECT s.song_name, ss.like_count, ss.dislike_count, ss.score 
                FROM song_scores ss
                JOIN songs s ON ss.song_id = s.song_id
                WHERE ss.like_count > 0
                ORDER BY ss.score DESC 
                LIMIT 3
            """)
            print("\n Top Liked Songs:")
            for row in cur.fetchall():
                print(f"  • {row[0]} (likes: {row[1]}, dislikes: {row[2]}, score: {row[3]:.3f})")
            
            # Most disliked
            cur.execute("""
                SELECT s.song_name, ss.dislike_count, ss.like_count, ss.score 
                FROM song_scores ss
                JOIN songs s ON ss.song_id = s.song_id
                WHERE ss.dislike_count > 0
                ORDER BY ss.dislike_count DESC 
                LIMIT 3
            """)
            print("\n Most Disliked Songs:")
            for row in cur.fetchall():
                print(f"  • {row[0]} (dislikes: {row[1]}, likes: {row[2]}, score: {row[3]:.3f})")
        
        print("="*60)
        
    except Exception as e:
        print(f" Error checking database: {e}")
        print(traceback.format_exc())
    finally:
        cur.close()
        conn.close()

def test_database():
    """Test function to verify database is working"""
    print("\n TESTING DATABASE FUNCTIONS")
    print("="*50)
    
    # Test connection
    print("\n1. Testing connection...")
    conn = get_connection()
    if conn:
        print(" Connection test passed")
        conn.close()
    else:
        print(" Connection test failed")
        return
    
    # Test saving a song
    print("\n2. Testing save_songs_to_db...")
    test_song = [{
        'track_id': 'test_' + datetime.now().strftime('%Y%m%d%H%M%S'),
        'title': 'Test Song',
        'artist': 'Test Artist',
        'album': 'Test Album',
        'url': 'https://spotify.com/test',
        'preview_url': None,
        'album_cover': None,
        'popularity': 50
    }]
    saved = save_songs_to_db(test_song, 'happy')
    print(f"   Result: {saved} songs saved")
    
    # Test getting excluded songs
    print("\n3. Testing get_excluded_songs...")
    excluded = get_excluded_songs('happy')
    print(f"   Found {len(excluded)} excluded songs")
    
    # Test getting top songs
    print("\n4. Testing get_top_scoring_songs...")
    top = get_top_scoring_songs('happy', limit=2)
    print(f"   Found {len(top)} top songs")
    
    # Show final database state
    check_database()
    
    print("\n Test complete!")

# Initialize database when module is imported
if __name__ == "__main__":
    # Run test if script is executed directly
    init_database()
    test_database()
else:
    # Initialize when imported
    init_database()