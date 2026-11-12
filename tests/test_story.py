import copy
from datetime import date
import unittest
from tests.test_pipeline import FakeAPI
from ohaasa.sources import SIGNS
from ohaasa.story import ready, publish_story


class StorySafety(unittest.TestCase):
    def test_only_today_after_both_posts(self):
        state={'date':'2026-11-12','source':'ohaasa','content':{'date':'2026-11-12','source':'ohaasa','rows':[{'rank':i+1,'sign':s} for i,s in enumerate(SIGNS)]},'carousel':{'status':'published'},'reel':{'status':'published'}}
        self.assertTrue(ready(state,date(2026,11,12)))
        with self.assertRaises(ValueError): ready(state,date(2026,11,13))
        state['reel']['status']='processing'
        self.assertFalse(ready(state,date(2026,11,12)))

    def test_story_request_and_no_duplicates(self):
        api=FakeAPI();state={'story_image':'https://example.test/story.jpg'}
        saved=[]
        publish_story(api,state,lambda s:saved.append(copy.deepcopy(s)),lambda:True)
        self.assertEqual(api.created,[{'media_type':'STORIES','image_url':state['story_image']}])
        self.assertTrue(saved[-2]['story']['attempted'])
        publish_story(api,state,lambda s:None,lambda:True)
        self.assertEqual(len(api.published),1)

    def test_ambiguous_result_is_not_republished(self):
        api=FakeAPI();api.fail=True;state={'story_image':'https://example.test/story.jpg'}
        with self.assertRaises(RuntimeError): publish_story(api,state,lambda s:None,lambda:True)
        with self.assertRaises(RuntimeError): publish_story(api,state,lambda s:None,lambda:True)
        self.assertEqual(len(api.published),1)
        api.current='PUBLISHED'
        publish_story(api,state,lambda s:None,lambda:True)
        self.assertEqual(state['story']['status'],'published')

    def test_midnight_and_state_write_failure(self):
        api=FakeAPI();state={'story_image':'https://example.test/story.jpg'}
        with self.assertRaises(ValueError): publish_story(api,state,lambda s:None,lambda:False)
        self.assertEqual(api.created,[])
        state['story']={'container':'123'}
        def fail(s): raise RuntimeError('storage down')
        with self.assertRaises(RuntimeError): publish_story(api,state,fail,lambda:True)
        self.assertEqual(api.published,[])


if __name__=='__main__': unittest.main()
