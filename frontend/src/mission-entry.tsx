import React from'react';
import{createRoot}from'react-dom/client';
import MissionControl from'./MissionControl';
import DemoEnhancements from'./DemoEnhancements';
import JudgeDemoCore from'./JudgeDemoCore';
import PublicMissionControl from'./PublicMissionControl';

const root=document.getElementById('mission-root');
const publicReadOnly=import.meta.env.VITE_PUBLIC_READ_ONLY==='true';

if(root)createRoot(root).render(
 <React.StrictMode>
  {publicReadOnly?<PublicMissionControl/>:<><MissionControl/><DemoEnhancements/><JudgeDemoCore/></>}
 </React.StrictMode>
);
