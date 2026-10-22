# Spotify Listening History

A python program that uses MySql to save and store data of a user using their API key. It shows the user their last 50 songs; each song will show the artist's ID, the artist name(s), song name, and the date when the song was played.

# How it works

It accesses the Sql database first, then, using the API keys given, would store the data into specific tables, then display the last 50 songs played. The tables created are called "tracks", "artists", "tracks_artists", and "plays". The main things to look at are the track ID's and artist ID's, which are unique to each song and artist.

<br> In terminal, type in streamlit run app.py to open application

# .env file

<br>SPOTIPY_CLIENT_ID=
<br>SPOTIPY_CLIENT_SECRET=
<br>SPOTIPY_REDIRECT_URI=

<br>DB_USER=
<br>DB_HOST=localhost
<br>DB_PASSWORD=
<br>DB_NAME=spotify_history


<br>Usually, the user would be root, and localhost does not change, but in specific cases it will.
<br>Open Spotify Developer, create a new app, then input the keys necessary here.
<br>Ex. the REDIRECT can be http://127.0.0.1:8888/callback
<br>Want it to be http://..... 


# packages needed

pip install spotipy mysql-connector-python python-dotenv
<br>pip install streamlit pandas 