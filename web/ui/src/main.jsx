import React from "react";
import { createRoot } from "react-dom/client";
import axios from "axios";

function App(){
  const [jobs,setJobs] = React.useState([]);
  const [nodes,setNodes] = React.useState([]);
  async function load(){
    try{
      const r1 = await axios.get("/farm/list_pending");
      setJobs(r1.data.tasks||[]);
      const r2 = await axios.get("/farm/nodes");
      setNodes(r2.data.nodes||[]);
    }catch(e){ console.error(e) }
  }
  React.useEffect(()=>{ load(); const id=setInterval(load,3000); return ()=>clearInterval(id); },[]);
  return <div style={{padding:20,fontFamily:"sans-serif"}}>
    <h2>Render Farm — Dashboard</h2>
    <button onClick={load}>Refresh</button>
    <h3>Nodes</h3>
    <pre>{JSON.stringify(nodes,null,2)}</pre>
    <h3>Pending Tasks (sample)</h3>
    <table border="1" cellPadding="6"><thead><tr><th>task</th><th>job</th><th>frame</th><th>status</th></tr></thead>
    <tbody>{jobs.slice(0,50).map((t,i)=>{ try{ const o=JSON.parse(t); return <tr key={i}><td>{o.task_id}</td><td>{o.job_id}</td><td>{o.payload.frame}</td><td>{o.status}</td></tr>}catch(e){return null}})}</tbody></table>
  </div>;
}

createRoot(document.getElementById("root")).render(<App/>);
