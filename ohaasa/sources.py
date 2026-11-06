from datetime import date
import json
import re

import requests
from bs4 import BeautifulSoup

ABC = 'https://www.asahi.co.jp/data/ohaasa2020/horoscope.json'
GOGO = 'https://www.tv-asahi.co.jp/goodmorning/uranai/'
SIGNS = ['양자리','황소자리','쌍둥이자리','게자리','사자자리','처녀자리',
         '천칭자리','전갈자리','사수자리','염소자리','물병자리','물고기자리']
JP = ['おひつじ座','おうし座','ふたご座','かに座','しし座','おとめ座',
      'てんびん座','さそり座','いて座','やぎ座','みずがめ座','うお座']


class NotReady(ValueError):
    """The official source has not published the target day yet."""


def source_for(day):
    return 'gogo' if day.weekday() >= 5 else 'ohaasa'


def validate_rows(rows):
    if [r['rank'] for r in rows] != list(range(1, 13)):
        raise ValueError('Expected exactly ranks 1–12, without duplicates.')
    if set(r['sign'] for r in rows) != set(SIGNS):
        raise ValueError('Expected all twelve different zodiac signs.')
    for row in rows:
        if not row['body'].strip() or not row['item'].strip():
            raise ValueError('Missing horoscope or lucky hint.')
    return rows


def parse_abc(raw, day):
    data = json.loads(raw)
    records = [r for r in data if r.get('onair_date') == day.strftime('%Y%m%d')]
    if len(records) != 1:
        raise NotReady('ABC does not contain the requested date: ' + str(day))
    rows = []
    for r in records[0]['detail']:
        parts = r['horoscope_text'].split('\t')
        if len(parts) < 2:
            raise ValueError('ABC format changed; review the source.')
        rows.append(dict(rank=int(r['ranking_no']), sign=SIGNS[int(r['horoscope_st'])-1],
                         body=' '.join(p.strip() for p in parts[:-1] if p.strip()),
                         item=parts[-1].strip(), color=''))
    return validate_rows(sorted(rows, key=lambda r: r['rank']))


def parse_gogo(raw, day):
    soup = BeautifulSoup(raw, 'html.parser')
    heading = soup.select_one('.rank-area .ttl-area')
    if not heading:
        raise ValueError('GoGo date heading missing; markup may have changed.')
    match = re.search(r'(\d+)月(\d+)日[（(]([A-Za-z]+)', heading.get_text())
    if not match:
        raise ValueError('GoGo date format changed.')
    weekday = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][day.weekday()]
    if (int(match[1]), int(match[2]), match[3].lower()) != (day.month, day.day, weekday.lower()):
        raise NotReady('GoGo has not updated to ' + str(day))
    # This source prints month/day/weekday, not a year. Never relabel a historical fetch.
    rows = []
    for link in soup.select('.rank-box a'):
        rank_image = link.select_one('img.rank')
        rank_match = re.search(r'rank-(\d+)\.png', rank_image['src']) if rank_image else None
        name = link.select_one('span').get_text(strip=True)
        if not rank_match or name not in JP:
            raise ValueError('Unknown GoGo ranking entry.')
        block = soup.select_one(link['href'] + ' .read-area')
        if not block or not block.select_one('p.read'):
            raise ValueError('GoGo detail missing.')
        text = block.get_text(' ', strip=True)
        hints = re.search(r'ラッキーカラー\s*[：:]\s*(.*?)\s*幸運のカギ\s*[：:]\s*(.+)', text)
        if not hints:
            raise ValueError('GoGo lucky color/key missing.')
        rows.append(dict(rank=int(rank_match[1]), sign=SIGNS[JP.index(name)],
                         body=block.select_one('p.read').get_text(strip=True),
                         color=hints[1].strip(), item=hints[2].strip()))
    return validate_rows(rows)


def fetch(day, source=None):
    source = source or source_for(day)
    url = ABC if source == 'ohaasa' else GOGO
    r = requests.get(url, timeout=(15, 45), headers={'User-Agent':'daily-ohaasa/1.0', 'Cache-Control':'no-cache'})
    if r.status_code != 200 or not r.content:
        raise RuntimeError(f'Official source request failed ({r.status_code}).')
    raw = r.content.decode('utf-8-sig')
    rows = (parse_abc if source == 'ohaasa' else parse_gogo)(raw, day)
    return dict(date=day.isoformat(), source=source, source_url=url, rows=rows)
