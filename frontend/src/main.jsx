import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

function App() {
  const [cameras, setCameras] = useState([]);
  const [events, setEvents] = useState([]);
  const [error, setError] = useState("");
  const refresh = () => {
    setError("");
    return Promise.all([fetch("/api/phase8/cameras"), fetch("/api/events")]).then(async ([cameraResponse, eventResponse]) => {
      if (!cameraResponse.ok || !eventResponse.ok) throw new Error("Backend unavailable");
      setCameras(await cameraResponse.json());
      setEvents(await eventResponse.json());
    }).catch(() => setError("Backend unavailable"));
  };
  useEffect(() => { refresh(); }, []);
  return <main>
    <nav><span className="brand">AVP</span><span className="mono">PHASE_08 / OPERATIONS</span><button>Settings</button></nav>
    <section className="hero"><p className="eyebrow">ABANDONED-OBJECT PLATFORM</p><h1>Camera runtime.<br />Operator clarity.</h1><p className="lead">Multi-camera health, bounded frame processing, and evidence events in one view.</p><button className="primary" onClick={refresh}>Refresh status</button></section>
    {error && <section className="alert">{error}</section>}
    <section className="grid"><article><p className="eyebrow">CAMERAS</p><strong>{cameras.length}</strong><span>runtime sources</span></article><article><p className="eyebrow">RUNTIME</p><strong>{cameras.some((camera) => camera.state === "connected") ? "LIVE" : cameras.length ? "READY" : "—"}</strong><span>fair scheduler</span></article><article><p className="eyebrow">SEARCH</p><strong>RESERVED</strong><span>future capability</span></article></section>
    <section className="panel"><div><p className="eyebrow">CAMERA REGISTRY</p><h2>{cameras.length ? "Camera health" : "No cameras configured"}</h2>{cameras.map((camera) => <p className="camera" key={camera.camera_id}><b>{camera.camera_id}</b><span>{camera.source_type} · {camera.state} · queue {camera.queue_depth}</span></p>)}</div><button className="secondary" onClick={refresh}>Refresh API</button></section>
    <section className="panel"><div><p className="eyebrow">EVENT TIMELINE</p><h2>{events.length ? `${events.length} candidate event${events.length === 1 ? "" : "s"}` : "No events yet"}</h2>{events.slice(0, 5).map((event) => <p className="camera" key={event.event_id}><b>{event.event_type}</b><span>{event.camera_id} · {Number(event.timestamp_s || 0).toFixed(2)}s</span></p>)}</div></section>
  </main>;
}

createRoot(document.getElementById("root")).render(<App />);
