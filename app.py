from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import openai
import json
from flask_cors import CORS
from dotenv import load_dotenv

app = Flask(__name__)

app.config['SESSION_COOKIE_NAME'] = 'Spotify OpenAI Cookie'
app.secret_key = 'iwhrefpirewuhg@IU#308urewf#2948!@#(EI)'
TOKEN_INFO = 'token_info'
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')
CORS(app, resources={r"*": {"origins": "https://aispotifyplaylists.martinestrin.com"}})

@app.route('/')
def home():
    auth_url = create_spotify_oauth().get_authorize_url()
    return redirect(auth_url)

@app.route('/redirect')
def redirect_page():
    session.clear()
    code = request.args.get('code')
    token_info = create_spotify_oauth().get_access_token(code)
    session[TOKEN_INFO] = token_info
    return redirect(url_for('generate_playlist', _external=True))

def create_spotify_oauth():
    return SpotifyOAuth(
                        client_id='57270bf393474d4f9f0da304ae3438cf',
                        client_secret='25c5421ff0bb4751b0b396cbc9078936',
                        redirect_uri=url_for('redirect_page', _external=True),
                        scope='user-library-read playlist-modify-private playlist-modify-public'
                        )

@app.route('/generate_playlist', methods=['GET', 'POST'])
def generate_playlist():
    if request.method == 'POST':
        playlist_name = request.form.get('playlist_name')
        prompt = request.form.get('prompt')

        try:
            token_info = session.get(TOKEN_INFO, None)
            if not token_info:
                return redirect('/')

            completion = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=
                [
                    {
                        "role": "system",
                        "content": ("Return a playlist of songs that fits the following description:\n" + prompt +
                                    "Do not provide anything in your response besides the names of the songs, each seperated by a comma. " +
                                    "No other punctuation, newline characters or text.")
                    }
                ]
            )
            response = completion.choices[0].message.content

            songs = response.strip().split(',')
            songs = set(response.split(','))
            playlist_id = create_playlist(songs, playlist_name)
            

            return redirect(url_for('display_playlist', playlist_id=playlist_id))
        
        except Exception as e:
            return jsonify({"error": str(e)})

    return render_template('index.html')

def create_playlist(songs, name):
    try:
        token_info = session.get(TOKEN_INFO, None)
    except:
        return redirect('/')
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    user_info = sp.me()
    user_id = user_info['id']
    playlist_name = name
    playlist = sp.user_playlist_create(user=user_id, name=playlist_name, public=False, collaborative=False)

    track_uris = []
    for song in songs:
        track_result = sp.search(q=song, type='track', limit=1)
        if track_result['tracks']['items']:
            track_uri = track_result['tracks']['items'][0]['uri']
            track_uris.append(track_uri)

    if track_uris:
        sp.user_playlist_add_tracks(user=user_id, playlist_id=playlist['id'], tracks=track_uris)
        return playlist['id']
    else:
        return "No valid songs found. Please check the song list and try again."

@app.route('/display_playlist/<playlist_id>', methods=['GET'])
def display_playlist(playlist_id):
    token_info = session.get(TOKEN_INFO, None)
    if not token_info:
        return redirect('/')
    sp = spotipy.Spotify(auth=token_info['access_token'])
    playlist = sp.playlist(playlist_id)
    return render_template('playlist.html', playlist=playlist)

if __name__ == '__main__':
    app.run(debug=True, port=8888)
