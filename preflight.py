"""Cheap no-dependency check before installing fonts/renderer on repeat cron runs."""
import base64
from datetime import datetime, timezone, timedelta
import json
import os
import urllib.request
import urllib.error

now=datetime.now(timezone(timedelta(hours=9)))
needed=True
if os.getenv('RUN_MODE')=='publish':
    if not 7 <= now.hour < 10:
        needed=False
    else:
        repo=os.environ['GITHUB_REPOSITORY']
        url=f'https://api.github.com/repos/{repo}/contents/.state/{now.date()}.json'
        request=urllib.request.Request(url,headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],
                                                    'Accept':'application/vnd.github+json'})
        try:
            with urllib.request.urlopen(request,timeout=30) as response:
                state=json.loads(base64.b64decode(json.load(response)['content']))
            needed=not all(state.get(k,{}).get('status')=='published' for k in ('carousel','reel'))
        except urllib.error.HTTPError as exc:
            if exc.code!=404: raise SystemExit('Preflight cannot read GitHub publishing state.')
        except urllib.error.URLError:
            raise SystemExit('Preflight cannot connect to GitHub.')
with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as stream:
    stream.write('needed='+str(needed).lower()+'\n')
print('Work needed:',needed)
