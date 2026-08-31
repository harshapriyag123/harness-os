import React from'react';
import{createRoot}from'react-dom/client';
import MissionControl from'./MissionControl';
const root=document.getElementById('mission-root');
if(root)createRoot(root).render(<React.StrictMode><MissionControl/></React.StrictMode>);
