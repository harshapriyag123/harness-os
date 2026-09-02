import React from'react';
import{createRoot}from'react-dom/client';
import MissionControl from'./MissionControl';
import DemoEnhancements from'./DemoEnhancements';
import PublicMissionControl from'./PublicMissionControl';
import JudgeMission from'./JudgeMission';

const root=document.getElementById('mission-root');
const publicReadOnly=import.meta.env.VITE_PUBLIC_READ_ONLY==='true';
const hostedJudge=import.meta.env.VITE_HOSTED_JUDGE==='true';

if(root)createRoot(root).render(
 <React.StrictMode>
  {publicReadOnly?<PublicMissionControl/>:<>{hostedJudge&&<JudgeMission/>}<MissionControl/><DemoEnhancements/></>}
 </React.StrictMode>
);
