from recommendspot import get_recommendations_for_emotion
import random

# Test the recommendation system
emotions = ['happy', 'sad', 'angry', 'neutral']
emotion = random.choice(emotions)
print(f'Testing emotion: {emotion}')

try:
    recs = get_recommendations_for_emotion(emotion, limit=5)
    print(f'Got {len(recs)} recommendations')
    for i, song in enumerate(recs):
        print(f'{i+1}. {song["title"]} by {song["artist"]} (likes: {song["likes"]}, dislikes: {song["dislikes"]})')
except Exception as e:
    print(f'Error: {e}')