from __future__ import annotations
import json,os
from dataclasses import dataclass
from typing import Any,Iterator
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen

class TrueForgeError(RuntimeError): pass

@dataclass(frozen=True)
class TrueForgeClient:
 base_url:str
 token:str|None=None
 timeout:float=10
 @classmethod
 def from_env(cls): return cls(os.getenv('TRUEFORGE_BASE_URL','http://127.0.0.1:8790').rstrip('/'),os.getenv('TRUEFORGE_TOKEN') or None)
 def _request(self,method:str,path:str,payload:dict[str,Any]|None=None)->dict[str,Any]:
  headers={'Accept':'application/json'}
  if payload is not None:headers['Content-Type']='application/json'
  if self.token:headers['Authorization']=f'Bearer {self.token}'
  request=Request(f'{self.base_url}{path}',method=method,headers=headers,data=json.dumps(payload).encode() if payload is not None else None)
  try:
   with urlopen(request,timeout=self.timeout) as response:body=json.loads(response.read() or b'{}')
  except HTTPError as exc:
   raw=exc.read().decode(errors='replace');raise TrueForgeError(f'TrueForge {method} {path} returned {exc.code}: {raw[:500]}') from exc
  except URLError as exc:raise TrueForgeError(f'TrueForge unavailable at {self.base_url}: {exc.reason}') from exc
  return body.get('data',body)
 def capabilities(self):return self._request('GET','/api/v1/capabilities')
 def create_session(self,agent_name:str):return self._request('POST','/api/v1/sessions',{'agent':{'name':agent_name}})
 def get_session(self,session_id:str):return self._request('GET',f'/api/v1/sessions/{session_id}')
 def submit_task(self,session_id:str,task:str,stream:bool=False):return self._request('POST',f'/api/v1/sessions/{session_id}/turns',{'input':[{'content':task,'type':'user.message'}],'previous_turn_id':'auto','stream':stream})
 def list_session_events(self,session_id:str):return self._request('GET',f'/api/v1/sessions/{session_id}/events')
 def list_turn_events(self,session_id:str,turn_id:str):return self._request('GET',f'/api/v1/sessions/{session_id}/turns/{turn_id}/events')
 def cancel_session(self,session_id:str):return self._request('POST',f'/api/v1/sessions/{session_id}/cancel')
