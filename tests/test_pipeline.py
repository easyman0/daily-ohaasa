import copy
from datetime import date,datetime,timezone
import json
import unittest

from ohaasa.sources import parse_abc,parse_gogo,source_for,NotReady,SIGNS,JP
from ohaasa.translate import validate_translation
from ohaasa.instagram import publish_kind
from ohaasa.main import publish_window


def abc_fixture():
    return [{'onair_date':'20261106','detail':[
        {'ranking_no':str(i),'horoscope_st':f'{i:02}',
         'horoscope_text':'本文\t助言\t\t\t青色'} for i in range(1,13)]}]


def gogo_fixture():
    ranks=''.join(f'<a href="#s{i}"><img class="rank" src="images/rank-{i+1}.png"><span>{name}</span></a>' for i,name in enumerate(JP))
    details=''.join(f'<div id="s{i}"><div class="read-area"><p class="read">助言</p><span>ラッキーカラー</span>：青<br><span>幸運のカギ</span>：カフェ</div></div>' for i in range(12))
    return '<div class="rank-area"><p class="ttl-area">11月7日（Sat）の占い</p></div><ul class="rank-box">'+ranks+'</ul>'+details


class Sources(unittest.TestCase):
    def test_weekend_and_kst(self):
        self.assertEqual(source_for(date(2026,11,6)),'ohaasa')
        self.assertEqual(source_for(date(2026,11,7)),'gogo')
        self.assertEqual(source_for(date(2026,11,8)),'gogo')
        self.assertTrue(publish_window(datetime(2026,11,6,22,0,tzinfo=timezone.utc)))
        self.assertFalse(publish_window(datetime(2026,11,6,21,59,tzinfo=timezone.utc)))

    def test_stale_abc(self):
        with self.assertRaises(NotReady): parse_abc(json.dumps(abc_fixture()),date(2026,11,7))

    def test_duplicate_ranking(self):
        data=abc_fixture();data[0]['detail'][1]['ranking_no']='1'
        with self.assertRaises(ValueError): parse_abc(json.dumps(data),date(2026,11,6))

    def test_all_signs_and_hints(self):
        rows=parse_abc(json.dumps(abc_fixture()),date(2026,11,6))
        self.assertEqual(rows[0]['item'],'青色')
        self.assertEqual(rows[0]['body'],'本文 助言')
        self.assertEqual(len(rows),12)

    def test_gogo_date_and_hint(self):
        rows=parse_gogo(gogo_fixture(),date(2026,11,7))
        self.assertEqual(rows[0]['color'],'青')
        self.assertEqual(rows[0]['item'],'カフェ')
        with self.assertRaises(NotReady): parse_gogo(gogo_fixture(),date(2026,11,8))

    def test_gogo_missing_hint(self):
        with self.assertRaises(ValueError): parse_gogo(gogo_fixture().replace('幸運のカギ','changed'),date(2026,11,7))

    def test_translation_cannot_change_rank(self):
        source={'source':'ohaasa','rows':parse_abc(json.dumps(abc_fixture()),date(2026,11,6))}
        translated={'rows':[{'rank':i+1,'sign':s,'lines':['좋은 하루예요.','차분히 지내요.'],'item':'파란색','color':''} for i,s in enumerate(SIGNS)]}
        validate_translation(translated,source)
        translated['rows'][0]['rank']=2
        with self.assertRaises(ValueError):validate_translation(translated,source)


class FakeAPI:
    def __init__(self):self.created=[];self.published=[];self.fail=False;self.current='FINISHED'
    def create(self,**data):self.created.append(data);return str(len(self.created))
    def wait(self,c):return 'FINISHED'
    def status(self,c):return self.current
    def publish(self,c):
        self.published.append(c)
        if self.fail:raise RuntimeError('Network disconnected after submission')
        return 'media-'+c


class Publishing(unittest.TestCase):
    def setUp(self):
        self.api=FakeAPI();self.saved=[]
        self.state={'images':['https://example.test/'+str(i)+'.jpg' for i in range(5)],
                    'video':'https://example.test/reel.mp4','captions':{'carousel':'card','reel':'reel'}}
    def save(self,s):self.saved.append(copy.deepcopy(s))

    def test_no_reposting_completed_carousel(self):
        publish_kind(self.api,self.state,'carousel',self.save)
        publish_kind(self.api,self.state,'carousel',self.save)
        publish_kind(self.api,self.state,'reel',self.save)
        self.assertEqual(len(self.api.published),2)
        self.assertEqual(len(self.api.created),7)

    def test_ambiguous_publish_never_retried(self):
        self.api.fail=True
        with self.assertRaises(RuntimeError):publish_kind(self.api,self.state,'carousel',self.save)
        self.assertTrue(self.saved[-1]['carousel']['attempted'])
        with self.assertRaises(RuntimeError):publish_kind(self.api,self.state,'carousel',self.save)
        self.assertEqual(len(self.api.published),1)
        self.api.current='PUBLISHED'
        publish_kind(self.api,self.state,'carousel',self.save)
        self.assertEqual(self.state['carousel']['status'],'published')
        self.assertEqual(len(self.api.published),1)

    def test_state_write_failure_stops_publish(self):
        self.state['carousel']={'container':'123'}
        def fail(_):raise RuntimeError('State storage failed')
        with self.assertRaises(RuntimeError):publish_kind(self.api,self.state,'carousel',fail)
        self.assertEqual(self.api.published,[])


if __name__=='__main__':unittest.main()
