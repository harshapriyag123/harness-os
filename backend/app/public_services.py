from __future__ import annotations
import json,os,time,threading
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen

_CACHE_COND=threading.Condition();_CACHE={'at':0.0,'value':None};_REFRESHING=False

def _targets():
    return [('Refund Fixture',os.getenv('PUBLIC_REFUND_FIXTURE_URL','https://harness-os.onrender.com/health')),('FaultLine MCP',os.getenv('PUBLIC_FAULTLINE_HEALTH_URL','https://faultline-h005.onrender.com/health'))]

def _timeout():
    try:value=float(os.getenv('PUBLIC_SERVICE_PROBE_TIMEOUT_SECONDS','3'))
    except (TypeError,ValueError):value=3.0
    return value if 0.25<=value<=10 else 3.0

def _ttl():
    try:value=float(os.getenv('PUBLIC_SERVICE_CACHE_SECONDS','10'))
    except (TypeError,ValueError):value=10.0
    return value if 0<=value<=300 else 10.0

def _probe(name:str,url:str):
    started=time.monotonic()
    try:
        request=Request(url,headers={'Accept':'application/json','User-Agent':'Harness-OS-Local-UI'})
        with urlopen(request,timeout=_timeout()) as response:raw=response.read().decode('utf-8','replace');status=response.status
        try:payload=json.loads(raw)
        except (TypeError,ValueError,json.JSONDecodeError):payload={'body':raw[:240]}
        return {'name':name,'url':url,'reachable':200<=status<400,'http_status':status,'latency_ms':round((time.monotonic()-started)*1000),'detail':payload}
    except (HTTPError,URLError,TimeoutError,OSError,ValueError) as exc:
        return {'name':name,'url':url,'reachable':False,'http_status':getattr(exc,'code',None),'latency_ms':round((time.monotonic()-started)*1000),'detail':str(exc)}

def snapshot(force:bool=False):
    global _REFRESHING
    ttl=_ttl();now=time.monotonic()
    with _CACHE_COND:
        cached=_CACHE['value'];age=now-_CACHE['at']
        if not force and cached is not None and age<ttl:return cached
        if _REFRESHING:
            if cached is not None:return cached
            _CACHE_COND.wait(timeout=_timeout()+1.0)
            if _CACHE['value'] is not None:return _CACHE['value']
        _REFRESHING=True
    try:
        targets=_targets()
        with ThreadPoolExecutor(max_workers=max(1,len(targets))) as pool:services=list(pool.map(lambda pair:_probe(*pair),targets))
        result={'services':services,'probed_at_epoch_ms':round(time.time()*1000),'cache_ttl_seconds':ttl}
        with _CACHE_COND:
            _CACHE.update({'at':time.monotonic(),'value':result});_REFRESHING=False;_CACHE_COND.notify_all()
        return result
    except Exception:
        with _CACHE_COND:_REFRESHING=False;_CACHE_COND.notify_all()
        raise
