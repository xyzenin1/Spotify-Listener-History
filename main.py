import mysql.connector
import os
import sys
from datetime import datetime, timezone

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

db_password = os.getenv("DB_PASSWORD")
db_user = os.getenv("DB_USER")
db_host = os.getenv("DB_HOST")

try:
    mycon = mysql.connector.connect(
        host=db_host,
        user=db_user,
        password=db_password
    )
    
    if mycon.is_connected():
        print("SQL connected successfully!")
except mysql.connector.Error as err:
    print("Error: ", err)
    sys.exit(1)
    
    
mycur = mycon.cursor()  # create cursor element
mycur.execute("CREATE DATABASE IF NOT EXISTS spotify_history_db")
print("Database created successfully")

mycur.execute("USE spotify_history_db")

mycur.execute("""
CREATE TABLE IF NOT EXISTS artists (
    artist_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL
)
""")

mycur.execute("""
CREATE TABLE IF NOT EXISTS tracks (
    track_id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    album_name VARCHAR(255),
    release_date VARCHAR(10),
    duration_ms INT,
    popularity INT
)
""")

mycur.execute("""
CREATE TABLE IF NOT EXISTS tracks_artists (
    track_id VARCHAR(50),
    artist_id VARCHAR(50),
    PRIMARY KEY (track_id, artist_id),
    FOREIGN KEY(track_id) REFERENCES tracks(track_id),
    FOREIGN KEY(artist_id) REFERENCES artists(artist_id)
)
""")

mycur.execute("""
CREATE TABLE IF NOT EXISTS plays (
    play_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    track_id VARCHAR(50) NOT NULL,
    played_at DATETIME NOT NULL,
    UNIQUE KEY uq_play (track_id, played_at),
    FOREIGN KEY(track_id) REFERENCES tracks(track_id)
)
""")

print("Tables Created Successfully")


def spotify_client():
    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(scope="user-read-recently-played")
    )


def parse_time(s):
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def save_play(cur, item):
    track = item["track"]
    if not track.get("id"):
        return 0
    
    cur.execute("""
    INSERT INTO tracks (
        track_id,
        name,
        album_name,
        release_date,
        duration_ms,
        popularity
    )
    VALUES (%s,%s,%s,%s,%s,%s)
    ON DUPLICATE KEY UPDATE popularity = VALUES(popularity)
    """, (
        track["id"],
        track["name"],
        track["album"]["name"],
        track["album"]["release_date"],
        track["duration_ms"],
        track.get("popularity"),
        )
    )
    
    for artist in track["artists"]:
        if not artist.get("id"):
            continue
        cur.execute("""
        INSERT IGNORE INTO artists (
            artist_id,
            name
        )
        VALUES (%s,%s)
        """, (artist["id"], artist["name"])
        )
        
        cur.execute("""
        INSERT IGNORE INTO tracks_artists (
            track_id,
            artist_id
        )
        VALUES (%s,%s)
        """, (track["id"], artist["id"])
        )
    cur.execute("""
    INSERT IGNORE INTO plays (
        track_id,
        played_at
    )
    VALUES (%s,%s)
    """, (track["id"], parse_time(item["played_at"]))
    )
    return cur.rowcount


def display_table():
    mycur.execute("""
        SELECT
            GROUP_CONCAT(a.artist_id ORDER BY a.name SEPARATOR ', ') AS artist_ids,
            GROUP_CONCAT(a.name ORDER BY a.name SEPARATOR ', ') AS artist_names,
            t.name,
            p.played_at
        FROM plays p
        JOIN tracks t ON p.track_id = t.track_id
        JOIN tracks_artists ta ON t.track_id = ta.track_id
        JOIN artists a ON ta.artist_id = a.artist_id
        GROUP BY p.play_id, t.name, p.played_at
        ORDER BY p.played_at DESC
    """)

    rows = mycur.fetchall()

    print(f"\n{'ARTIST ID(S)':<46} {'ARTIST(S)':<32} {'TRACK':<36} {'DATE PLAYED'}")
    print("-" * 136)

    for artist_ids, artist_names, track_name, played_at in rows:
        local_time = played_at.replace(tzinfo=timezone.utc).astimezone()

        print(
            f"{artist_ids[:44]:<46} "
            f"{artist_names[:30]:<32} "
            f"{track_name[:34]:<36} "
            f"{local_time:%Y-%m-%d %I:%M %p}"
        )

    print(f"\n{len(rows)} plays")
    
    
def display_new_plays(new_items):
    print("\nNEW PLAYS THIS RUN")
    print(f"{'ARTIST(S)':<40} {'TRACK':<40} {'DATE PLAYED'}")
    print("-" * 136)

    if not new_items:
        print("No new plays since last run.")
        return

    for item in new_items:
        track = item["track"]
        artist_names = ", ".join(a["name"] for a in track["artists"])

        # Spotify's timestamp is UTC, so convert to your computer's local time
        played_at = parse_time(item["played_at"])
        local_time = played_at.replace(tzinfo=timezone.utc).astimezone()

        print(
            f"{artist_names[:38]:<40} "
            f"{track['name'][:38]:<40} "
            f"{local_time:%Y-%m-%d %I:%M %p}"
        )

    print(f"\n{len(new_items)} new plays")
        
    
    
def main():
    sp = spotify_client()
    items = sp.current_user_recently_played(limit=50)["items"]
    
    print(f"Fetched {len(items)} recently played from Spotify")
    
    new_plays = 0
    for item in items:
        new_plays += save_play(mycur, item)
        
    new_items = []
    for item in items:
        if save_play(mycur, item):
            new_items.append(item)
        
    mycon.commit()
    
    print(f"Saved {new_plays} new plays")
    
    display_new_plays(new_items)
    display_table()
    mycur.close()
    mycon.close()
    
    
    
if __name__ == "__main__":
    main()