import React from'react';
import{createRoot}from'react-dom/client';
import MissionControl from'./MissionControl';
import DemoEnhancements from'./DemoEnhancements';
const root=document.getElementById('mission-root');
if(root)createRoot(root).render(<React.StrictMode><MissionControl/><DemoEnhancements/></React.StrictMode>);
