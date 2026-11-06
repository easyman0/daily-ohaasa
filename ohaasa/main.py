import argparse
from datetime import date, datetime, time
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from .sources import fetch, source_for, NotReady
from .translate import translate, validate_translation
from .render import render, captions
from .github import GitHub
from .instagram import Instagram, active_token, publish_kind

KST=ZoneInfo('Asia/Seoul')


def publish_window(now):
    return time(7) <= now.astimezone(KST).time().replace(tzinfo=None) < time(10,30)


def run(args):
    now=datetime.now(KST)
    today=now.date()
    day=date.fromisoformat(args.date) if args.date else today
    out=Path('build')/str(day)
    github=None
    state={}
    live=args.mode=='publish'
    if live:
        if args.fixture or args.date or args.translated or args.source!='auto':
            raise ValueError('Publishing only accepts live, automatic, current-day content.')
        if os.getenv('AUTO_PUBLISH')!='true':
            raise ValueError('AUTO_PUBLISH must be true after setup verification.')
        if not publish_window(now):
            raise ValueError('Publishing is restricted to 07:00–10:30 KST.')
        github=GitHub()
        github.ensure_public()
        state,_=github.read(f'.state/{day}.json')
        if all(state.get(k,{}).get('status')=='published' for k in ('carousel','reel')):
            print('Both posts already published; nothing to do.')
            return
        # Verify credentials and destination before translation/storage side effects.
        api=Instagram(active_token(github))
        api.verify_account()
    if not state.get('images'):
        if state.get('content'):
            data=state['content']
        else:
            if args.fixture:
                source=json.loads(Path(args.fixture).read_text(encoding='utf-8'))
                if source['date']!=str(day): raise ValueError('Fixture date mismatch.')
            else:
                try:
                    source=fetch(day,None if args.source=='auto' else args.source)
                except NotReady:
                    if live and now.hour<9:
                        print('Today’s source is not ready. No post was made; next scheduled run will retry.')
                        return
                    raise
            if args.translated:
                data=validate_translation(json.loads(Path(args.translated).read_text(encoding='utf-8')),source)
            else:
                data=translate(source)
            if live:
                state.update(date=str(day),source=source_for(day),content=data)
                github.save(f'.state/{day}.json',state)
        render(data,out)
        text=captions(data)
        for kind,caption in text.items(): (out/(kind+'-caption.txt')).write_text(caption,encoding='utf-8')
        (out/'source.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        if not live:
            print('Preview generated in '+str(out.resolve())+'. No Instagram or GitHub writes were made.')
            return
        files=[out/f'{i:02}.jpg' for i in range(1,6)]+[out/'reel.mp4',out/'source.json',
                  out/'carousel-caption.txt',out/'reel-caption.txt']
        urls=github.release_assets(str(day),files)
        state.update(images=[urls[f'{i:02}.jpg'] for i in range(1,6)],video=urls['reel.mp4'],captions=text)
        github.save(f'.state/{day}.json',state)
    if datetime.now(KST).date()!=day or not publish_window(datetime.now(KST)):
        raise ValueError('Posting window expired during preparation; nothing further published.')
    if state['date']!=str(day) or state['source']!=source_for(day):
        raise ValueError('Stored source/date does not match today’s policy.')
    save=lambda value:github.save(f'.state/{day}.json',value)
    publish_kind(api,state,'carousel',save)
    publish_kind(api,state,'reel',save)
    print('Carousel and reel published. IDs are saved in .state/'+str(day)+'.json')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['preview','publish'],default='preview')
    parser.add_argument('--source',choices=['auto','ohaasa','gogo'],default='auto')
    parser.add_argument('--date',help='Preview only: date of a saved fixture, never relabel live content.')
    parser.add_argument('--fixture',help='Preview only: saved parsed source JSON.')
    parser.add_argument('--translated',help='Preview only: manually reviewed translated JSON.')
    args=parser.parse_args()
    if args.date and not args.fixture:
        parser.error('--date requires a historical fixture; live fetches always use today.')
    try:
        run(args)
    except Exception as exc:
        # Do not dump SDK/request tracebacks which might contain credentials.
        print(f'ERROR: {type(exc).__name__}: {exc}')
        raise SystemExit(1)


if __name__=='__main__': main()
