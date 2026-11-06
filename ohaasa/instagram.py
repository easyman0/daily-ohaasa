import hashlib
import json
import os
import time
from datetime import datetime, timezone
import requests
from cryptography.fernet import Fernet


def login_mode():
    mode = os.getenv('IG_LOGIN_MODE') or 'unified'
    if mode not in ('unified', 'instagram'):
        raise ValueError('IG_LOGIN_MODE must be unified or instagram.')
    return mode


def active_token(github):
    """Persist refreshed tokens encrypted; never commit plaintext tokens."""
    seed=os.environ['IG_ACCESS_TOKEN']
    # Unified Login uses a business integration system-user token, not an
    # Instagram user token. Never send it to the legacy refresh endpoint.
    # Keep it only in Actions Secrets. The configured token expires in 60 days;
    # unified-token renewal must be configured separately before that deadline.
    if login_mode() == 'unified':
        return seed
    cipher=Fernet(os.environ['STATE_ENCRYPTION_KEY'].encode())
    fingerprint=hashlib.sha256(seed.encode()).hexdigest()
    saved,_=github.read('.state/auth.json')
    now=time.time()
    if not saved or saved.get('seed_fingerprint')!=fingerprint:
        # Initial secret must be a freshly issued LONG-LIVED Instagram Login token.
        payload={'token':seed,'refreshed_at':now}
    else:
        payload=json.loads(cipher.decrypt(saved['encrypted'].encode()))
    if now-payload['refreshed_at'] >= 7*86400:
        try:
            r=requests.get('https://graph.instagram.com/refresh_access_token',
                           params={'grant_type':'ig_refresh_token','access_token':payload['token']},timeout=(15,60))
        except requests.RequestException:
            raise RuntimeError('Instagram token refresh connection failed.') from None
        if not r.ok or 'access_token' not in r.json():
            raise RuntimeError('Instagram token refresh failed; reconnect the Instagram account.')
        payload={'token':r.json()['access_token'],'refreshed_at':now}
    if not saved or payload['refreshed_at']!=saved.get('refreshed_at') or saved.get('seed_fingerprint')!=fingerprint:
        github.save('.state/auth.json',{'seed_fingerprint':fingerprint,'refreshed_at':payload['refreshed_at'],
                    'encrypted':cipher.encrypt(json.dumps(payload).encode()).decode()})
    # Mask rotated tokens as well as the original Actions secret.
    if os.getenv('GITHUB_ACTIONS')=='true': print('::add-mask::'+payload['token'])
    return payload['token']


class Instagram:
    def __init__(self,token,user_id=None):
        self.user_id=user_id or os.environ['IG_USER_ID']
        version=os.getenv('IG_API_VERSION') or 'v27.0'
        host = 'graph.facebook.com' if login_mode() == 'unified' else 'graph.instagram.com'
        self.base='https://'+host+'/'+version
        self.session=requests.Session()
        self.session.headers['Authorization']='Bearer '+token

    def request(self,method,path,**kwargs):
        # No automatic retry for POST. Publishing is not an idempotent endpoint.
        try:
            r=self.session.request(method,self.base+'/'+path,timeout=(15,60),**kwargs)
        except requests.RequestException:
            raise RuntimeError('Instagram connection failed; inspect saved publishing state.') from None
        if not r.ok:
            try: code=r.json().get('error',{}).get('code','unknown')
            except ValueError: code='unknown'
            raise RuntimeError(f'Instagram request failed (HTTP {r.status_code}, code {code}).')
        return r.json()

    def verify_account(self):
        me=self.request('GET',self.user_id,params={'fields':'id,username'})
        expected=os.getenv('IG_USERNAME') or 'daily_ohaasa'
        if me.get('username','').lower()!=expected.lower().lstrip('@'):
            raise ValueError('Connected Instagram account does not match @'+expected)

    def create(self,**data):
        return self.request('POST',self.user_id+'/media',data=data)['id']

    def status(self,container):
        return self.request('GET',container,params={'fields':'status_code'})['status_code']

    def wait(self,container):
        deadline=time.monotonic()+300
        while time.monotonic()<deadline:
            status=self.status(container)
            if status in ('FINISHED','PUBLISHED'): return status
            if status in ('ERROR','EXPIRED'): raise RuntimeError('Instagram container '+status)
            time.sleep(10)
        raise RuntimeError('Instagram processing timed out; the next run will check the same container.')

    def publish(self,container):
        return self.request('POST',self.user_id+'/media_publish',data={'creation_id':container})['id']


def publish_kind(api,state,kind,save):
    """Persist each boundary. Never repeat an ambiguous media_publish request."""
    item=state.setdefault(kind,{})
    if item.get('status')=='published': return
    if item.get('attempted'):
        if api.status(item['container'])=='PUBLISHED':
            item['status']='published'
            item['reconciled']=True
            save(state)
            return
        raise RuntimeError(f'{kind}: previous publish outcome uncertain. Review Instagram before resetting this state.')
    if not item.get('container'):
        if kind=='carousel':
            children=item.setdefault('children',[])
            for url in state['images'][len(children):]:
                child=api.create(image_url=url,is_carousel_item='true')
                children.append(child)
                save(state)
            for child in children: api.wait(child)
            container=api.create(media_type='CAROUSEL',children=','.join(children),caption=state['captions'][kind])
        else:
            container=api.create(media_type='REELS',video_url=state['video'],
                                 caption=state['captions'][kind],share_to_feed='false')
        item['container']=container
        save(state)
    api.wait(item['container'])
    # Save *before* transmission. A crash after this point requires reconciliation,
    # not blindly posting again on the next cron run.
    item['attempted']=True
    save(state)
    media_id=api.publish(item['container'])
    item.update(status='published',media_id=media_id,
                published_at=datetime.now(timezone.utc).isoformat())
    save(state)
