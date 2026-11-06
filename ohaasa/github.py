import base64
import json
import mimetypes
import os
from urllib.parse import quote
import requests


class GitHub:
    def __init__(self,repo=None,token=None):
        self.repo=repo or os.environ['GITHUB_REPOSITORY']
        self.session=requests.Session()
        self.session.headers.update({'Authorization':'Bearer '+(token or os.environ['GITHUB_TOKEN']),
                                     'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
        self.base='https://api.github.com/repos/'+self.repo

    def request(self,method,path,**kwargs):
        r=self.session.request(method,self.base+path,timeout=(15,90),**kwargs)
        if r.status_code==404 and method=='GET': return None
        if not r.ok: raise RuntimeError(f'GitHub {method} failed ({r.status_code}); check permissions.')
        return r.json() if r.content else None

    def read(self,path):
        item=self.request('GET','/contents/'+quote(path,safe='/'))
        if not item: return {}, None
        return json.loads(base64.b64decode(item['content'])),item['sha']

    def save(self,path,data):
        _,sha=self.read(path)
        body={'message':'Update daily publishing state',
              'content':base64.b64encode(json.dumps(data,ensure_ascii=False,indent=2).encode()).decode()}
        if sha: body['sha']=sha
        self.request('PUT','/contents/'+quote(path,safe='/'),json=body)

    def ensure_public(self):
        meta=self.request('GET','')
        if not meta or meta['private']:
            raise ValueError('This setup needs a public repository for public Instagram media URLs.')

    def release_assets(self,day,paths):
        tag='daily-'+day
        release=self.request('GET','/releases/tags/'+tag)
        if release is None:
            release=self.request('POST','/releases',json={
                'tag_name':tag,'name':'Daily ohaasa '+day,'make_latest':'false',
                'body':'Generated posting assets. The original source is recorded in source.json.'})
        existing={a['name']:a for a in release['assets']}
        urls={}
        for p in paths:
            if p.name not in existing:
                endpoint=release['upload_url'].split('{')[0]
                with p.open('rb') as stream:
                    r=self.session.post(endpoint,params={'name':p.name},data=stream,
                                        headers={'Content-Type':mimetypes.guess_type(p.name)[0] or 'application/octet-stream'},
                                        timeout=(15,180))
                if not r.ok: raise RuntimeError(f'Media storage failed ({r.status_code}).')
                existing[p.name]=r.json()
            urls[p.name]=existing[p.name]['browser_download_url']
        return urls
