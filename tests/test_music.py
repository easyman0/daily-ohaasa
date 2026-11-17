import copy
from datetime import date, timedelta
import json
import os
import unittest
import subprocess
import tempfile
from pathlib import Path
import imageio_ffmpeg
from unittest.mock import patch
from ohaasa.music import selected_track, TRACKS, prepare_audio_stream
from ohaasa.instagram import publish_kind
from tests.test_pipeline import FakeAPI


class Music(unittest.TestCase):
    def test_silent_aac_preserves_video_frames(self):
        ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'reel.mp4'
            subprocess.run([ffmpeg,'-y','-f','lavfi','-i','color=c=black:s=108x192:r=30:d=10','-an','-c:v','libx264',str(path)],check=True,capture_output=True)
            def frames():
                return subprocess.run([ffmpeg,'-i',str(path),'-map','0:v:0','-f','framemd5','-'],check=True,capture_output=True).stdout
            before=frames()
            prepare_audio_stream(path)
            self.assertEqual(frames(),before)
            probe=subprocess.run([ffmpeg,'-i',str(path),'-f','null','-'],check=True,capture_output=True)
            self.assertIn(b'Audio: aac',probe.stderr)
            self.assertIn(b'48000 Hz, stereo',probe.stderr)
            self.assertIn(b'Duration: 00:00:10.0',probe.stderr)

    def test_start_date_and_weekday_rotation(self):
        with patch.dict(os.environ, {'REEL_MUSIC': 'true'}):
            self.assertIsNone(selected_track('2026-11-17'))
            self.assertEqual(selected_track('2026-11-18')['title'], 'Piano Dreams')
            monday = date(2026, 11, 23)
            for i, track in enumerate(TRACKS):
                self.assertEqual(selected_track(str(monday+timedelta(days=i))),track)
                self.assertEqual(selected_track(str(monday+timedelta(days=i+7))),track)
        with patch.dict(os.environ, {'REEL_MUSIC': 'false'}):
            self.assertIsNone(selected_track('2026-11-18'))

    def test_music_persisted_and_retried_without_duplicate(self):
        api=FakeAPI()
        state={'date':'2026-11-18','video':'https://example.test/reel.mp4','captions':{'reel':'test'}}
        saved=[]
        api.fail=True
        with patch.dict(os.environ, {'REEL_MUSIC':'true'}):
            with self.assertRaises(RuntimeError):
                publish_kind(api,state,'reel',lambda s:saved.append(copy.deepcopy(s)))
        self.assertEqual(saved[0]['reel']['music'],TRACKS[2])
        config=json.loads(api.created[0]['audio_configuration'])
        self.assertEqual(config['audio_id'],TRACKS[2]['audio_id'])
        self.assertEqual(config['audio_volume'],35)
        with patch.dict(os.environ, {'REEL_MUSIC':'false'}):
            with self.assertRaises(RuntimeError):publish_kind(api,state,'reel',lambda s:None)
        self.assertEqual(len(api.created),1)
        self.assertEqual(len(api.published),1)

    def test_music_save_failure_prevents_container_creation(self):
        api=FakeAPI()
        state={'date':'2026-11-18','video':'test','captions':{'reel':'test'}}
        def fail(s):raise RuntimeError('state unavailable')
        with patch.dict(os.environ, {'REEL_MUSIC':'true'}):
            with self.assertRaises(RuntimeError):publish_kind(api,state,'reel',fail)
        self.assertEqual(api.created,[])
