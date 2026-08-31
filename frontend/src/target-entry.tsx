import React from'react';
import{createRoot}from'react-dom/client';
import TargetManager from'./TargetManager';
import'./target-manager.css';
const root=document.getElementById('target-manager-root');if(root)createRoot(root).render(<React.StrictMode><TargetManager/></React.StrictMode>);
