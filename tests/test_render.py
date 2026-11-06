import os
from pathlib import Path
import subprocess
import unittest
from PIL import Image,ImageChops
import imageio_ffmpeg
from ohaasa.render import render,render_cover,captions
from ohaasa.sources import SIGNS


@unittest.skipUnless(os.getenv('RENDER_SMOKE')=='1','Set RENDER_SMOKE=1 for media integration tests')
class Render(unittest.TestCase):
    def test_cloud_fonts_layout_and_video(self):
        data={'date':'2026-11-07','source':'gogo','rows':[
            {'rank':i+1,'sign':s,'lines':['주변의 이야기에 귀 기울여 보세요.',
             '차분하게 오늘의 계획을 정리해 보세요.','작은 노력도 소중히 여겨주세요.'],
             'color':'하늘색','item':'여행용 캐리어'} for i,s in enumerate(SIGNS)]}
        out=render(data,Path('build/smoke-test'))
        for i in range(1,6):
            p=out/f'{i:02}.jpg'
            with Image.open(p) as image:
                self.assertEqual(image.size,(1080,1440))
            self.assertLess(p.stat().st_size,8*1024*1024)
        ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
        probe=subprocess.run([ffmpeg,'-i',str(out/'reel.mp4'),'-f','null','-'],capture_output=True)
        self.assertEqual(probe.returncode,0)
        self.assertNotIn(b'Audio:',probe.stderr)
        reader=imageio_ffmpeg.read_frames(str(out/'reel.mp4'),pix_fmt='rgb24')
        meta=next(reader)
        self.assertEqual(meta['size'],(1080,1920))
        self.assertAlmostEqual(meta['duration'],10,places=1)
        reader.close()
        self.assertIn('행운의 색과 아이템을',captions(data)['carousel'])
        diff=ImageChops.difference(render_cover(data,True),render_cover(data,False))
        x1,y1,x2,y2=diff.getbbox()
        self.assertTrue(100<=x1<x2<=125 and 450<=y1<y2<=475)


if __name__=='__main__':unittest.main()
