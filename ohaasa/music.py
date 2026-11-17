"""Approved weekly Reel soundtrack, selected using the KST content date."""
from datetime import date
import json
import os

START_DATE = date(2026, 11, 18)
TRACKS = (
    {'audio_id': '2477944699150252', 'title': 'Peaceful Piano', 'artist': 'Dr. Pheel'},
    {'audio_id': '624445130386044', 'title': 'Lofi Love', 'artist': 'Ella Joy Meir'},
    {'audio_id': '445556344868453', 'title': 'Piano Dreams', 'artist': 'Ella Joy Meir'},
    {'audio_id': '1213218503365575', 'title': 'Lofi Memoir', 'artist': 'Adam Griffith'},
    {'audio_id': '3012618439128205', 'title': 'Piano In Bloom (Instrumental)', 'artist': 'Ella Joy Meir'},
    {'audio_id': '496700212782181', 'title': 'Lofi Magic', 'artist': 'Ella Joy Meir'},
    {'audio_id': '771177030946350', 'title': 'Piano Lullaby', 'artist': 'Ella Joy Meir'},
)


def selected_track(day):
    if os.getenv('REEL_MUSIC') != 'true' or not day:
        return None
    day = date.fromisoformat(day)
    if day < START_DATE:
        return None
    return dict(TRACKS[day.weekday()])


def audio_configuration(track):
    # Source video is silent. A restrained level suits the horoscope cards.
    return json.dumps({'audio_id': track['audio_id'], 'audio_volume': 35, 'video_volume': 1})
