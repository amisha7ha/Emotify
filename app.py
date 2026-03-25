# app.py
import streamlit as st
import cv2
import numpy as np
import time
import random
from recommendspot import get_recommendations_for_emotion
from emotion_detect import detect_emotion_from_frame
import cloud_database as db  # Changed from database to cloud_database

# ==============================
# PAGE CONFIG
# ==============================
st.set_page_config(page_title="Emotify", layout="wide")

# Custom CSS for beautiful modern UI
st.markdown("""
<style>
    /* Main container */
    .main {
        padding: 0rem 1rem;
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    }

    /* Hide default streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Force gradient background */
    .stApp {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    }

    /* Modern title styling */
    .emotify-title {
        font-size: 3.5rem;
        font-weight: 900;
        background: linear-gradient(135deg, #1e293b, #334155);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        margin-bottom: 0.3rem;
        letter-spacing: -2px;
    }

    .emotify-subtitle {
        text-align: center;
        color: #64748b;
        font-size: 1.1rem;
        margin-bottom: 2rem;
        letter-spacing: 0.5px;
        font-weight: 500;
    }

    /* Enhanced camera container */
    .camera-container {
        background: white;
        border-radius: 20px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }

    .camera-container:hover {
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }

    .camera-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 1rem;
        color: #1e293b;
        font-weight: 700;
        font-size: 1.1rem;
    }

    /* Enhanced status indicators */
    .status-box {
        background: linear-gradient(135deg, #1e293b, #334155);
        color: white;
        padding: 0.8rem 1.5rem;
        border-radius: 30px;
        text-align: center;
        font-weight: 600;
        margin: 0.5rem 0;
        display: inline-block;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        animation: fadeIn 0.5s ease-in;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* Premium now playing section */
    .now-playing {
        background: linear-gradient(135deg, #1e293b 0%, #334155 50%, #475569 100%);
        border-radius: 24px;
        padding: 1.8rem;
        margin: 1.5rem 0;
        color: white;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.1);
        position: relative;
        overflow: hidden;
    }

    .now-playing::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899);
    }

    .now-playing-title {
        color: white;
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 12px;
    }

    /* Enhanced buttons */
    .stButton > button {
        background: transparent !important;
        border: none !important;
        color: #475569 !important;
        font-size: 1rem !important;
        padding: 0.5rem 1rem !important;
        border-radius: 12px !important;
        transition: all 0.3s ease !important;
        font-weight: 600 !important;
    }

    .stButton > button:hover {
        background: #f1f5f9 !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }

    /* Premium like/dislike buttons */
    div[data-testid="column"] .stButton > button {
        font-size: 1.5rem !important;
        padding: 0.4rem 0.8rem !important;
        border-radius: 16px !important;
        background: rgba(255, 255, 255, 0.1) !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }

    div[data-testid="column"] .stButton > button:hover {
        background: rgba(255, 255, 255, 0.2) !important;
        transform: scale(1.1) translateY(-2px);
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
    }

    div[data-testid="column"] .stButton > button:disabled {
        opacity: 0.4 !important;
        transform: none !important;
    }

    /* Enhanced song title buttons */
    .song-title-btn .stButton > button {
        text-align: left !important;
        font-weight: 600 !important;
        color: #1e293b !important;
        padding: 0.8rem 1.2rem !important;
        border-radius: 16px !important;
        background: white !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease !important;
    }

    .song-title-btn .stButton > button:hover {
        color: #0f172a !important;
        background: #f8fafc !important;
        border-color: #cbd5e1 !important;
        transform: translateX(4px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    
    /* Enhanced mood badge */
    .mood-badge {
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        color: white;
        padding: 0.6rem 1.5rem;
        border-radius: 25px;
        font-size: 1rem;
        font-weight: 700;
        display: inline-block;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        animation: slideIn 0.6s ease-out;
    }

    @keyframes slideIn {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }

    /* Enhanced divider */
    .custom-divider {
        height: 2px;
        background: linear-gradient(90deg, transparent, #e2e8f0, #cbd5e1, #e2e8f0, transparent);
        margin: 2rem 0;
        border-radius: 1px;
    }

    /* Enhanced welcome container */
    .welcome-container {
        background: white;
        border-radius: 24px;
        padding: 3rem 2rem;
        text-align: center;
        border: 1px solid #e2e8f0;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        animation: bounceIn 0.8s ease-out;
    }

    @keyframes bounceIn {
        0% { opacity: 0; transform: scale(0.3); }
        50% { opacity: 1; transform: scale(1.05); }
        70% { transform: scale(0.9); }
        100% { opacity: 1; transform: scale(1); }
    }

    .welcome-container h3 {
        color: #1e293b;
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 1rem;
    }

    .welcome-container p {
        color: #64748b;
        font-size: 1.1rem;
        line-height: 1.6;
    }

    /* Enhanced checkbox styling */
    .stCheckbox {
        color: #1e293b;
    }

    .stCheckbox label {
        font-weight: 600;
        color: #374151;
    }

    /* Spotify play button enhancement */
    .spotify-play-btn {
        background: linear-gradient(135deg, #1db954, #1ed760);
        color: white !important;
        padding: 0.6rem 1.5rem !important;
        border-radius: 25px !important;
        font-weight: 700 !important;
        text-decoration: none !important;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 6px -1px rgba(29, 185, 84, 0.3);
    }

    .spotify-play-btn:hover {
        background: linear-gradient(135deg, #1ed760, #1db954) !important;
        transform: translateY(-2px);
        box-shadow: 0 8px 12px -1px rgba(29, 185, 84, 0.4);
        text-decoration: none !important;
    }

    /* Section headers */
    .section-header {
        color: #1e293b;
        font-size: 1.5rem;
        font-weight: 700;
        margin: 1.5rem 0 1rem 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    /* Ensure all text is properly colored */
    p, h1, h2, h3, h4, h5, h6, span, div {
        color: #374151;
    }

    /* Loading spinner enhancement */
    .stSpinner > div {
        border-color: #3b82f6 transparent transparent transparent !important;
    }
</style>
""", unsafe_allow_html=True)

# ==============================
# HEADER
# ==============================
st.markdown('<h1 class="emotify-title">EMOTIFY</h1>', unsafe_allow_html=True)
st.markdown('<p class="emotify-subtitle">AI-Powered Mood Detection & Music Recommendations</p>', unsafe_allow_html=True)

# ==============================
# SESSION STATE
# ==============================
if "camera_stopped" not in st.session_state:
    st.session_state.camera_stopped = False
if "detected_emotion" not in st.session_state:
    st.session_state.detected_emotion = None
if "recommendations" not in st.session_state:
    st.session_state.recommendations = []
if "current_track" not in st.session_state:
    st.session_state.current_track = None
if "session_id" not in st.session_state:
    st.session_state.session_id = str(random.randint(10000, 99999))
if "feedback_given" not in st.session_state:
    st.session_state.feedback_given = {}
if "detection_completed" not in st.session_state:
    st.session_state.detection_completed = False
if "db_initialized" not in st.session_state:
    st.session_state.db_initialized = False

# Initialize Neon database (only once per session)
if not st.session_state.db_initialized:
    db.init_database()
    st.session_state.db_initialized = True

# ==============================
# MAIN CONTENT
# ==============================
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="camera-container">', unsafe_allow_html=True)
    st.markdown('<div class="camera-header">� Live Camera Feed</div>', unsafe_allow_html=True)

    # Webcam control - this also serves as restart
    if not st.session_state.detection_completed:
        run = st.checkbox("🎬 Start Emotion Detection", key="webcam_toggle")
    else:
        # When detection is completed, show option to restart
        restart = st.checkbox("🔄 Start New Detection", value=False, key="restart_toggle")
        if restart:
            # Reset all states when restarting
            st.session_state.camera_stopped = False
            st.session_state.detected_emotion = None
            st.session_state.recommendations = []
            st.session_state.current_track = None
            st.session_state.feedback_given = {}
            st.session_state.detection_completed = False
            st.rerun()
        run = False

    FRAME_WINDOW = st.image([])
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    status_area = st.empty()
    music_area = st.container()

# ==============================
# MAIN LOOP
# ==============================
if run and not st.session_state.camera_stopped:
    cap = cv2.VideoCapture(0)
    
    with status_area:
        st.markdown('<div class="status-box">🔴 Camera Active - Show your emotion to the camera</div>', unsafe_allow_html=True)
    
    while run:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        emotion, conf, triggered, box = detect_emotion_from_frame(frame)

        if triggered:
            with status_area:
                st.markdown(f'<div class="status-box">✨ Detected: {emotion.upper()} ({conf*100:.1f}% confidence)</div>', unsafe_allow_html=True)

            with st.spinner(f"🎵 Finding perfect {emotion} songs for you..."):
                recs = get_recommendations_for_emotion(emotion, limit=5)

            if recs and len(recs) >= 3:
                st.session_state.detected_emotion = emotion
                st.session_state.recommendations = recs
                st.session_state.current_track = recs[0]
                st.session_state.camera_stopped = True
                st.session_state.detection_completed = True
                run = False
            else:
                with status_area:
                    st.markdown('<div class="status-box">❌ Could not find songs. Please try again.</div>', unsafe_allow_html=True)

            cap.release()
            break

        if box:
            x, y, w, h = box
            cv2.rectangle(frame, (x, y), (x+w, y+h), (154, 165, 129), 3)
            cv2.putText(frame, f"{emotion} ({conf*100:.1f}%)", (x, y-12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (56, 66, 43), 2)

        FRAME_WINDOW.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        time.sleep(0.01)

    if cap.isOpened():
        cap.release()

# ==============================
# SHOW RECOMMENDATIONS
# ==============================
if st.session_state.camera_stopped and st.session_state.recommendations:
    
    with music_area:
        # Mood badge
        st.markdown(f'<div class="mood-badge">✨ Feeling {st.session_state.detected_emotion.upper()}</div>', unsafe_allow_html=True)
        
        # Currently Playing
        if st.session_state.current_track:
            main_track = st.session_state.current_track
            track_id = main_track['track_id']
            
            feedback_key = f"{track_id}_{st.session_state.detected_emotion}"
            has_feedback = feedback_key in st.session_state.feedback_given
            
            embed_url = f"https://open.spotify.com/embed/track/{track_id}"
            
            st.markdown(f"""
            <div class="now-playing">
                <div class="now-playing-title">
                    <span>🎵 NOW PLAYING</span>
                </div>
                <iframe src="{embed_url}"
                width="100%" height="80"
                frameBorder="0"
                allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
                style="border-radius: 12px; margin-bottom: 1rem;">
                </iframe>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="color: white; font-weight: 700; font-size: 1.1rem; margin-bottom: 0.2rem;">{main_track['title']}</div>
                        <div style="color: rgba(255,255,255,0.9); font-size: 1rem;">{main_track['artist']}</div>
                    </div>
                    <a href="{main_track['url']}" target="_blank" class="spotify-play-btn">▶️ Open in Spotify</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Like/Dislike for current track
            col_l1, col_l2, _ = st.columns([1, 1, 8])
            
            with col_l1:
                if has_feedback and st.session_state.feedback_given[feedback_key] == 'like':
                    st.button("👍", key="like_current_disabled", disabled=True)
                else:
                    if st.button("👍", key="like_current"):
                        db.add_feedback(track_id, st.session_state.detected_emotion, 
                                      'like', st.session_state.session_id)
                        st.session_state.feedback_given[feedback_key] = 'like'
            
            with col_l2:
                if has_feedback and st.session_state.feedback_given[feedback_key] == 'dislike':
                    st.button("👎", key="dislike_current_disabled", disabled=True)
                else:
                    if st.button("👎", key="dislike_current"):
                        db.add_feedback(track_id, st.session_state.detected_emotion, 
                                      'dislike', st.session_state.session_id)
                        st.session_state.feedback_given[feedback_key] = 'dislike'
        
        # Divider
        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
        
        # More Recommendations (Perfectly aligned 4 songs)
        st.markdown('<div class="section-header">🎵 More Recommendations</div>', unsafe_allow_html=True)
        
        other_tracks = [
            song for song in st.session_state.recommendations 
            if song['track_id'] != st.session_state.current_track['track_id']
        ]
        
        for i, song in enumerate(other_tracks[:4]):
            track_id = song['track_id']
            
            # Clickable song title only (no like/dislike in expanded list)
            cols = st.columns([1])
            with cols[0]:
                st.markdown('<div class="song-title-btn">', unsafe_allow_html=True)
                if st.button(f"{song['title']} — {song['artist']}", key=f"song_{i}", use_container_width=True):
                    st.session_state.current_track = song
                st.markdown('</div>', unsafe_allow_html=True)

elif not run and not st.session_state.detection_completed:
    with col2:
        st.markdown("""
        <div class="welcome-container">
            <h3>🎭 Welcome to Emotify!</h3>
            <p>Experience the future of music discovery powered by AI emotion detection.</p>
            <p style="font-size: 1rem; margin-top: 1rem;">Simply click "Start Emotion Detection" and let your facial expressions guide you to the perfect playlist.</p>
            <div style="margin-top: 1.5rem; font-size: 0.9rem; color: #6b7280;">
                ✨ AI analyzes your mood in real-time<br>
                🎵 Curated songs match your emotions<br>
                💝 Your feedback improves recommendations
            </div>
        </div>
        """, unsafe_allow_html=True)

# ==============================
# MY LIBRARY SECTION - REMOVED (Using Neon instead)
# ==============================
# The library section has been removed as requested
# All data is now stored in Neon cloud database