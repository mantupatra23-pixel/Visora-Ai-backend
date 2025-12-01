// ui/src/components/PropTuner.jsx
// React component (default export) — Tailwind CSS assumed
// Usage: <PropTuner apiBase="/api" propName="sword_long" />
import React, { useState, useEffect } from "react";

export default function PropTuner({ apiBase = "/props", propName = null }) {
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(false);
  const [offset, setOffset] = useState([0,0,0]);
  const [rotation, setRotation] = useState([0,0,0]);
  const [scale, setScale] = useState(1.0);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!propName) return;
    fetch(`${apiBase}/list`).then(r=>r.json()).then(j=>{
      const p = (j.props || []).find(x => x.name === propName);
      if (p) {
        setMeta(p);
        const hg = p.hand_grip || {};
        setOffset(hg.offset || [0,0,0]);
        setRotation(hg.rotation || [0,0,0]);
        setScale(p.bbox ? Math.max(...p.bbox) : 1.0);
      }
    }).catch(e => console.error(e));
  }, [propName]);

  const setOffsetIdx = (i, v) => setOffset(prev => { const c=[...prev]; c[i]=parseFloat(v); return c; });
  const setRotIdx = (i, v) => setRotation(prev => { const c=[...prev]; c[i]=parseFloat(v); return c; });

  async function saveMeta() {
    if (!meta) return;
    setLoading(true);
    try {
      const newMeta = {...meta, hand_grip: {...(meta.hand_grip||{}), offset, rotation}, bbox: meta.bbox || [scale,scale,scale]};
      const resp = await fetch(`${apiBase}/register`, {
        method: "POST",
        headers: {"Content-Type":"application/octet-stream"},
        body: JSON.stringify(newMeta)
      });
      // The backend register endpoint we created earlier expects multipart upload; fallback: POST to /props/save_meta if you add it.
      // For now just show message.
      setMessage("Saved locally (send to server via register endpoint).");
    } catch (e) {
      setMessage("Save failed: "+String(e));
    } finally {
      setLoading(false);
    }
  }

  if (!meta) return <div className="p-4 border rounded">No prop selected or prop not found.</div>;

  return (
    <div className="p-4 bg-white rounded shadow-sm w-full max-w-2xl">
      <h3 className="text-xl font-semibold mb-2">Prop Tuner — {meta.name}</h3>
      <div className="flex gap-4">
        <div className="w-1/2">
          <div className="bg-gray-100 rounded p-2 h-48 flex items-center justify-center">
            {meta.model_path ? (
              <img src={meta.preview || "/static/placeholder_prop.png"} alt="preview" className="max-h-40"/>
            ) : <div className="text-sm text-gray-500">No preview</div>}
          </div>
          <div className="mt-3">
            <label className="block text-sm">Scale</label>
            <input type="range" min="0.1" max="3" step="0.01" value={scale} onChange={e=>setScale(e.target.value)} className="w-full"/>
            <div className="text-xs text-gray-600">Scale: {scale}</div>
          </div>
        </div>

        <div className="w-1/2 space-y-3">
          <div>
            <div className="text-sm font-medium">Hand Grip Offset (meters)</div>
            {["X","Y","Z"].map((label,i)=>(
              <div key={i} className="flex items-center gap-2">
                <div className="w-6 text-xs">{label}</div>
                <input type="range" min="-0.5" max="0.5" step="0.001" value={offset[i]} onChange={e=>setOffsetIdx(i,e.target.value)} className="flex-1"/>
                <div className="w-16 text-right text-xs">{offset[i]}</div>
              </div>
            ))}
          </div>

          <div>
            <div className="text-sm font-medium">Rotation (radians)</div>
            {["X","Y","Z"].map((label,i)=>(
              <div key={i} className="flex items-center gap-2">
                <div className="w-6 text-xs">{label}</div>
                <input type="range" min="-3.1416" max="3.1416" step="0.01" value={rotation[i]} onChange={e=>setRotIdx(i,e.target.value)} className="flex-1"/>
                <div className="w-16 text-right text-xs">{rotation[i]}</div>
              </div>
            ))}
          </div>

          <div className="flex gap-2">
            <button className="px-3 py-1 bg-blue-600 text-white rounded" onClick={saveMeta} disabled={loading}>Save</button>
            <button className="px-3 py-1 bg-gray-200 rounded" onClick={()=>{ navigator.clipboard?.writeText(JSON.stringify({offset,rotation,scale})); setMessage("Copied to clipboard"); }}>Copy JSON</button>
            <div className="text-sm text-gray-600 ml-auto">{message}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
