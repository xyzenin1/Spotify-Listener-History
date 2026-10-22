import os
from zoneinfo import available_timezones

import mysql.connector
import pandas as pd
import altair as alt
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Spotify History", page_icon="🎧", layout="wide")

QUERY = """
    SELECT
        p.play_id,
        p.played_at,
        t.track_id,
        t.name AS track,
        t.album_name,
        t.duration_ms,
        a.artist_id,
        a.name AS artist
    FROM plays p
    JOIN tracks t ON p.track_id = t.track_id
    JOIN tracks_artists ta ON t.track_id = ta.track_id
    JOIN artists a ON ta.artist_id = a.artist_id
"""



@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    """One row per (play, artist). Cached for 5 minutes."""
    con = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database="spotify_history_db",
    )
    cur = con.cursor(dictionary=True)
    cur.execute(QUERY)
    rows = cur.fetchall()
    cur.close()
    con.close()
    return pd.DataFrame(rows)





st.title("🎧 Spotify Listening History")

try:
    long_df = load_data()
except mysql.connector.Error as err:
    st.error(f"Could not connect to MySQL: {err}")
    st.stop()

if long_df.empty:
    st.info("No plays in the database yet. Run `python main.py` first.")
    st.stop()





st.sidebar.header("Filters")

tz_names = sorted(available_timezones())
tz = st.sidebar.selectbox("Time zone", tz_names, index=tz_names.index("UTC"))

if st.sidebar.button("Refresh data"):
    st.cache_data.clear()
    st.rerun()





long_df["played_at"] = (
    pd.to_datetime(long_df["played_at"]).dt.tz_localize("UTC").dt.tz_convert(tz)
)

min_date = long_df["played_at"].dt.date.min()
max_date = long_df["played_at"].dt.date.max()
date_range = st.sidebar.date_input(
    "Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = date_range
else:
    start = end = date_range[0] if isinstance(date_range, tuple) else date_range

selected_artists = st.sidebar.multiselect(
    "Artists", sorted(long_df["artist"].unique())
)




mask = (long_df["played_at"].dt.date >= start) & (long_df["played_at"].dt.date <= end)
long_df = long_df[mask]

if selected_artists:
    keep_ids = long_df.loc[long_df["artist"].isin(selected_artists), "play_id"].unique()
    long_df = long_df[long_df["play_id"].isin(keep_ids)]

if long_df.empty:
    st.warning("No plays match these filters.")
    st.stop()




plays = long_df.groupby(
    ["play_id", "played_at", "track_id", "track", "album_name", "duration_ms"],
    as_index=False,
    dropna=False,
).agg(artists=("artist", lambda s: ", ".join(sorted(s))))




total_minutes = plays["duration_ms"].sum() / 60000
c1, c2, c3, c4 = st.columns(4)
c1.metric("Plays", f"{len(plays):,}")
c2.metric("Unique tracks", f"{plays['track_id'].nunique():,}")
c3.metric("Unique artists", f"{long_df['artist_id'].nunique():,}")
c4.metric("Listening time", f"{total_minutes / 60:,.1f} hrs")





left, right = st.columns(2)

with left:
    st.subheader("Plays per day")
    per_day = plays.groupby(plays["played_at"].dt.date).size()
    st.bar_chart(per_day)

with right:
    st.subheader("Plays by hour of day")
    per_hour = (
        plays.groupby(plays["played_at"].dt.hour).size().reindex(range(24), fill_value=0)
    )
    hour_df = per_hour.rename_axis("hour").reset_index(name="plays")
    chart = (
        alt.Chart(hour_df)
        .mark_bar()
        .encode(
            x=alt.X(
                "hour:O",
                title="Hour of day",
                axis=alt.Axis(labelAngle=0, labelOverlap="parity"),
            ),
            y=alt.Y("plays:Q", title="Plays"),
            tooltip=["hour", "plays"],
        )
    )
    st.altair_chart(chart)
    
    

left, right = st.columns(2)

with left:
    st.subheader("Top artists")
    top_artists = (
        long_df.groupby("artist")["play_id"].nunique().nlargest(10).sort_values()
    )
    st.bar_chart(top_artists, horizontal=True)

with right:
    st.subheader("Top tracks")
    top_tracks = (
        plays.groupby(["track", "artists"])
        .size()
        .reset_index(name="plays")
        .sort_values("plays", ascending=False)
        .head(10)
    )
    st.dataframe(top_tracks, hide_index=True, use_container_width=True)




st.subheader("Recent plays")
recent = plays.sort_values("played_at", ascending=False).head(50).copy()
recent["played_at"] = recent["played_at"].dt.strftime("%Y-%m-%d %I:%M %p")
st.dataframe(
    recent[["played_at", "track", "artists", "album_name"]],
    hide_index=True,
    use_container_width=True,
)