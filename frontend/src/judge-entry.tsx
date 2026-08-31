import React,{useEffect,useState}from'react';
import{createRoot}from'react-dom/client';
import{api}from'./lib/api';
import JudgeCertification from'./JudgeCertification';
import'./judge-certification.css';

function JudgeMode(){const[campaign,setCampaign]=useState<any>();useEffect(()=>{let alive=true;async function load(){try{const d=await api.dashboard();if(alive)setCampaign(d.campaigns?.[0])}catch{}}load();const t=setInterval(load,4000);return()=>{alive=false;clearInterval(t)}},[]);return <JudgeCertification campaign={campaign}/>}
const root=document.getElementById('certification-root');if(root)createRoot(root).render(<React.StrictMode><JudgeMode/></React.StrictMode>);
