"""Approved weekly Reel soundtrack, selected using the KST content date."""
from datetime import date
import json
import os
from pathlib import Path
import subprocess
import imageio_ffmpeg

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


def prepare_audio_stream(path):
    """Meta's music mixer needs an AAC stream; preserve the video bit-for-bit."""
    path=Path(path)
    target=path.with_name(path.stem+'-aac.mp4')
    result=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-i',str(path),
        '-f','lavfi','-i','anullsrc=channel_layout=stereo:sample_rate=48000',
        '-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','128k',
        '-shortest','-movflags','+faststart',str(target)],
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if result.returncode:
        raise RuntimeError('Silent AAC preparation for Reel music failed.')
    target.replace(path)
    return path
