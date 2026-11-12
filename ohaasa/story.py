"""Publish one dated story after both daily posts, using the same durable state."""
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw
from .render import render_cover, font, INK
from .sources import source_for, SIGNS
from .github import GitHub
from .instagram import Instagram, active_token

KST = ZoneInfo('Asia/Seoul')


def ready(state, day):
    if not all(state.get(k, {}).get('status') == 'published' for k in ('carousel', 'reel')):
        return False
    content = state.get('content', {})
    if state.get('date') != str(day) or content.get('date') != str(day):
        raise ValueError('Story must use today\'s published content.')
    if state.get('source') != source_for(day) or content.get('source') != source_for(day):
        raise ValueError('Story source does not match today\'s policy.')
    rows = content.get('rows', [])
    if [r.get('rank') for r in rows] != list(range(1, 13)) or {r.get('sign') for r in rows} != set(SIGNS):
        raise ValueError('Story ranking is invalid.')
    return True


def render_story(data, out):
    # Keep all essential content away from the top/bottom story controls.
    canvas = Image.new('RGB', (2160, 3840), '#f7f4ed')
    cover = render_cover(data).resize((1800, 2400), Image.Resampling.LANCZOS)
    canvas.paste(cover, (180, 460))
    draw = ImageDraw.Draw(canvas)
    for y, text in [(1530, '자세한 운세는 프로필의'), (1590, '오늘 게시물에서')]:
        f = font('bold', 34)
        width = draw.textlength(text, font=f)
        draw.text(((2160-width)/2, y*2), text, font=f, fill=INK, anchor='lt')
    # White heart drawn directly so it renders consistently on Windows/Linux.
    import math
    points=[]
    for i in range(121):
        t=2*math.pi*i/120
        x=16*math.sin(t)**3
        y=13*math.cos(t)-5*math.cos(2*t)-2*math.cos(3*t)-math.cos(4*t)
        points.append((1080+x*2.5, 3340-y*2.5))
    draw.polygon(points, fill='white')
    draw.line(points, fill='#8c9da5', width=3)
    out=Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    canvas.resize((1080,1920), Image.Resampling.LANCZOS).save(out, quality=96, subsampling=0)
    return out


def publish_story(api, state, save, still_today):
    item=state.setdefault('story', {})
    if item.get('status') == 'published':
        return
    if not still_today():
        raise ValueError('Story date changed; no publication attempted.')
    if item.get('attempted'):
        if api.status(item['container']) == 'PUBLISHED':
            item.update(status='published', reconciled=True)
            save(state)
            return
        raise RuntimeError('Story publish outcome uncertain; inspect Instagram before any retry.')
    if not item.get('container'):
        item['container']=api.create(media_type='STORIES', image_url=state['story_image'])
        save(state)
    api.wait(item['container'])
    if not still_today():
        raise ValueError('Story date changed during preparation.')
    item['attempted']=True
    save(state)
    media_id=api.publish(item['container'])
    item.update(status='published', media_id=media_id, published_at=datetime.now(KST).isoformat())
    save(state)


def main():
    if os.getenv('AUTO_PUBLISH') != 'true' or os.getenv('STORY_PUBLISH') != 'true':
        print('Story publishing is disabled.')
        return
    day=datetime.now(KST).date()
    github=GitHub()
    github.ensure_public()
    path=f'.state/{day}.json'
    state,_=github.read(path)
    if not ready(state, day):
        print('Today\'s carousel and reel are not both published; no story posted.')
        return
    if state.get('story', {}).get('status') == 'published':
        print('Today\'s story is already published; nothing to do.')
        return
    api=Instagram(active_token(github))
    api.verify_account()
    print('Instagram account verified; preparing today\'s story.')
    if not state.get('story_image'):
        image=render_story(state['content'], Path('build')/str(day)/'story.jpg')
        state['story_image']=github.release_assets(str(day), [image])['story.jpg']
        github.save(path,state)
    publish_story(api,state,lambda value:github.save(path,value),lambda:datetime.now(KST).date()==day)
    print('Today\'s story published. ID saved in '+path)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'ERROR: {type(exc).__name__}: {exc}')
        raise SystemExit(1)
