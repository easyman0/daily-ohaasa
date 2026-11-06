from datetime import date
from pathlib import Path
from functools import lru_cache
import math
import os
import random
import subprocess

from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

INK = '#49443e'
ACCENT = '#8c9da5'
S = 2
W, H = 1080, 1440


def font_file(weight):
    override = os.getenv('FONT_' + weight.upper())
    if override:
        return override
    local = Path('C:/Windows/Fonts') / {'regular':'malgun.ttf','bold':'malgunbd.ttf','number':'georgia.ttf'}[weight]
    if local.exists():
        return str(local)
    cloud = {'regular':'/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
             'bold':'/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
             'number':'/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf'}[weight]
    if not Path(cloud).exists():
        filename = Path(cloud).name
        matches = sorted(Path('/usr/share/fonts').rglob(filename))
        if not matches:
            raise FileNotFoundError('Required font missing: ' + filename)
        return str(matches[0])
    return cloud


@lru_cache(maxsize=128)
def font(weight, size):
    p = font_file(weight)
    if p.endswith('.ttc'):
        for index in range(10):
            try:
                candidate=ImageFont.truetype(p,round(size*S),index=index)
            except OSError:
                break
            if 'KR' in candidate.getname()[0]: return candidate
        raise ValueError('Korean font face not found in Noto collection.')
    return ImageFont.truetype(p, round(size*S))


def label(day):
    weekdays = ['월요일','화요일','수요일','목요일','금요일','토요일','일요일']
    return f'{day.year}年 {day.month}月{day.day}日 ({weekdays[day.weekday()]})'


def paper():
    rng = random.Random(17)
    im = Image.new('RGB',(W,H))
    im.putdata([(247+n,244+n,237+n) for n in (rng.choice([-1,0,0,0,1]) for _ in range(W*H))])
    return im.resize((W*S,H*S))


class Canvas:
    def __init__(self):
        self.im = paper()
        self.d = ImageDraw.Draw(self.im)

    def text(self,x,y,value,weight='regular',size=31,color=INK,width=None):
        for fs in range(size, 21, -1):
            f = font(weight,fs)
            if width is None or self.d.textlength(value,font=f) <= width*S:
                break
        else:
            raise ValueError('Text does not fit; not publishing: ' + value)
        if x*S+self.d.textlength(value,font=f) > (W-55)*S:
            raise ValueError('Text overflows card: ' + value)
        self.d.text((x*S,y*S),value,font=f,fill=color,anchor='lt')

    def line(self,pts,color=ACCENT,width=1):
        self.d.line([(round(x*S),round(y*S)) for x,y in pts],fill=color,width=max(1,round(width*S)))

    def orbit(self,detail=False):
        cx,cy,rx,ry = (876,194,112,38) if detail else (877,204,126,43)
        pts=[]
        for j in range(181):
            a=2*math.pi*j/180
            x,y=rx*math.cos(a),ry*math.sin(a)
            pts.append((cx+x*math.cos(-.58)-y*math.sin(-.58),cy+x*math.sin(-.58)+y*math.cos(-.58)))
        self.line(pts,'#bdc5c6',.65)
        for x,y,r in ([(822,150,9),(918,238,7)] if detail else [(819,157,10),(926,253,8)]):
            pts=[(x,y-r),(x+r*.24,y-r*.24),(x+r,y),(x+r*.24,y+r*.24),
                 (x,y+r),(x-r*.24,y+r*.24),(x-r,y),(x-r*.24,y-r*.24)]
            self.d.polygon([(round(a*S),round(b*S)) for a,b in pts],fill=ACCENT)

    def small(self):
        return self.im.resize((W,H),Image.Resampling.LANCZOS)


def render_cover(data, dot=True):
    c=Canvas()
    c.text(88,105,label(date.fromisoformat(data['date'])),size=32)
    c.text(86,175,'오하아사','bold',104)
    c.line([(94,319),(144,319)],width=2)
    c.text(92,342,'오늘의 별자리 순위',size=28)
    c.orbit()
    for i,row in enumerate(data['rows']):
        y=444+i*65
        c.text(140,y,f'{i+1:02}','number',42)
        c.text(236,y,row['sign'],'bold' if i<3 else 'regular',39)
    if dot:
        c.d.ellipse((109*S,458*S,119*S,468*S),fill=ACCENT)
    footer='@daily_ohaasa'
    width=c.d.textlength(footer,font=font('regular',25))/S
    c.text((W-width)/2,1344,footer,size=25)
    return c.small()


def render_card(data,page):
    c=Canvas()
    c.text(88,90,label(date.fromisoformat(data['date'])),size=29)
    c.text(86,151,'오하아사','bold',76)
    c.line([(92,262),(142,262)],width=2)
    c.text(90,284,f'오늘의 별자리 운세  ·  {page*3+1}—{page*3+3}위',size=27)
    c.orbit(True)
    for b in range(3):
        row=data['rows'][page*3+b]
        y=391+b*294
        c.text(91,y,f'{row["rank"]:02}','number',43,ACCENT)
        c.text(174,y-1,row['sign'],'bold',44)
        # Keep three lines clear of the two hint rows on weekends.
        for k,line in enumerate(row['lines']):
            c.text(174,y+69+k*38,line,size=31,width=804)
        if data['source']=='gogo':
            c.text(174,y+185,'행운의 색',size=24,color=ACCENT)
            c.text(354,y+183,row['color'],size=27,width=624)
            c.text(174,y+226,'행운 아이템',size=24,color=ACCENT)
            c.text(354,y+224,row['item'],size=27,width=624)
        else:
            c.text(174,y+222,'행운의 힌트',size=24,color=ACCENT)
            c.text(326,y+220,row['item'],size=27,width=652)
        if b<2:
            c.line([(174,y+271),(978,y+271)],'#deddd6',.6)
    c.text(90,1352,'@daily_ohaasa',size=24)
    return c.small()


def render_reel(data,out):
    canvas=Image.new('RGB',(1080,1920),(247,244,237))
    canvas.paste(render_cover(data,False),(0,240))
    draw=ImageDraw.Draw(canvas)
    draw.rectangle((0,0,1079,179),fill='black')
    draw.rectangle((0,1740,1079,1919),fill='black')
    bounds=(106,695,123,712)
    patch=canvas.crop(bounds)
    mask=Image.new('L',(34,34),0)
    ImageDraw.Draw(mask).ellipse((6,6,26,26),fill=255)
    mask=mask.resize((17,17),Image.Resampling.LANCZOS)
    dot=Image.new('RGB',(17,17),ACCENT)
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    path=out/'reel.mp4'
    cmd=[ffmpeg,'-y','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24',
         '-s','1080x1920','-r','30','-i','pipe:0','-an','-c:v','libx264',
         '-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',
         '-frames:v','300',str(path)]
    with (out/'ffmpeg.log').open('wb') as log:
        p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log)
        try:
            for i in range(300):
                frame=canvas.copy()
                opacity=(1+math.cos(2*math.pi*(i/30)/2.5))/2
                alpha=mask.point(lambda v:round(v*opacity))
                frame.paste(Image.composite(dot,patch,alpha),bounds[:2])
                if i==0: frame.save(out/'reel-preview.jpg',quality=95)
                p.stdin.write(frame.tobytes())
        finally:
            p.stdin.close()
            result=p.wait()
        if result: raise RuntimeError('Video encoding failed.')
    reader=imageio_ffmpeg.read_frames(str(path),pix_fmt='rgb24')
    meta=next(reader)
    count=sum(1 for _ in reader)
    if meta['size']!=(1080,1920) or count!=300 or abs(meta['duration']-10)>.05:
        raise ValueError('Video verification failed.')
    return path


def render(data,out,video=True):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    images=[render_cover(data)]+[render_card(data,p) for p in range(4)]
    for i,im in enumerate(images,1):
        # Originals retain the user's approved 3:4 layout. API gets JPEG, not PNG.
        im.save(out/f'{i:02}.jpg',quality=96,subsampling=0)
    preview=Image.new('RGB',(1656,444),'#e6e3dd')
    for i,im in enumerate(images):
        preview.paste(im.resize((324,432),Image.Resampling.LANCZOS),(6+i*330,6))
    preview.save(out/'preview.jpg',quality=95)
    if video: render_reel(data,out)
    return out


def captions(data):
    row=data['rows'][0]
    symbols=dict(zip(['양자리','황소자리','쌍둥이자리','게자리','사자자리','처녀자리',
                      '천칭자리','전갈자리','사수자리','염소자리','물병자리','물고기자리'],'♈♉♊♋♌♍♎♏♐♑♒♓'))
    title=label(date.fromisoformat(data['date']))+' 오하아사 ☾'
    hints='행운의 색과 아이템' if data['source']=='gogo' else '행운의 힌트'
    ending='좋은 말은 마음에 담고,\n조심할 일은 가볍게 참고하기.\n오늘도 나만의 속도로 좋은 하루 보내세요 🤍\n\n#오하아사 #운세 #별자리 #おは朝 #ohaasa'
    post=title+f'\n\n오늘의 1위는 {row["sign"]} {symbols[row["sign"]]}\n'+'\n'.join(row['lines'])
    particle='을' if data['source']=='gogo' else '를'
    post+=f'\n\n옆으로 넘기면 12개 별자리의 운세와\n{hints}{particle} 확인할 수 있어요.\n\n'+ending
    reel=title+f'\n\n오늘 내 별자리는 몇 위인가요? ✨\n\n별자리별 자세한 운세와 {hints}는\n프로필 @daily_ohaasa → 오늘의 게시물에서 확인해 주세요.\n\n'+ending
    return {'carousel':post,'reel':reel}
