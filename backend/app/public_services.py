from __future__ import annotations
import json,os,time
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen

DEFAULTS={
 'refund_fixture':('Refund Fixture',os.getenv('PUBLIC_REFUND_FIXTURE_URL','https://harness-os.onrender.com/health')),
 'faultline':('FaultLine MCP',os.getenv('PUBLIC_FAULTLINE_HEALTH_URL','https://faultline-h005.onrender.com/health')),
}

def _probe(name:str,url:str):
    started=time.time()
    try:
        request=Request(url,headers={'Accept':'application/json','User-Agent':'Harness-OS-Local-UI'})
        with urlopen(request,timeout=5) as response:
            raw=response.read().decode('utf-8','replace');status=response.status
        try: payload=json.loads(raw)
        except Exception: payload={'body':raw[:240]}
        return {'name':name,'url':url,'reachable':200<=status<400,'http_status':status,'latency_ms':round((time.time()-started)*1000),'detail':payload}
    except (HTTPError,URLError,TimeoutError,OSError) as exc:
        code=getattr(exc,'code',None)
        return {'name':name,'url':url,'reachable':False,'http_status':code,'latency_ms':round((time.time()-started)*1000),'detail':str(exc)}

def snapshot():
    return {'services':[_probe(name,url) for name,url in DEFAULTS.values()]}
