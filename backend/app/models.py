from typing import Literal
from pydantic import BaseModel,Field
class AgentCreate(BaseModel):
 repository_url:str=Field(min_length=3,max_length=500);branch:str=Field(default='main',min_length=1,max_length=200);name:str=Field(min_length=2,max_length=120);harness_type:Literal['TrueForge','Custom MCP Agent','Generic Agent']='TrueForge';config_path:str|None=None;instruction_path:str|None=None;mcp_config_path:str|None=None;policy_path:str|None=None
class CampaignCreate(BaseModel):
 agent_id:str;maximum_scenarios:int=Field(default=1,ge=1,le=100);maximum_runtime:int=Field(default=300,ge=10,le=3600);parallelism:int=Field(default=1,ge=1,le=10);fault_injection:bool=True;stop_on_critical:bool=True;categories:list[Literal['NORMAL','SECURITY','RELIABILITY','POLICY','RECOVERY']]=['RELIABILITY']
class InvariantUpdate(BaseModel):
 title:str|None=None;description:str|None=None;enabled:bool|None=None
class Decision(BaseModel):
 approver:str=Field(default='local-user',min_length=2,max_length=120);reason:str=Field(default='Reviewed verification evidence',min_length=2,max_length=1000)
