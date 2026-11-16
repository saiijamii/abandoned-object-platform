import React from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const metrics = [
  ["Detector", "YOLO / RF-DETR ready", "configurable backend"],
  ["Luggage recall", "—", "awaiting annotations"],
  ["Processing FPS", "—", "CPU benchmark pending"],
];

function App() {
  return <main>
    <nav><span className="brand">AVP</span><span className="mono">PHASE_01 / OPERATIONS</span><button>Settings</button></nav>
    <section className="hero"><p className="eyebrow">ABANDONED-OBJECT PLATFORM</p><h1>See luggage clearly.<br />Measure before alerting.</h1><p className="lead">Detector quality dashboard for CCTV evaluation. Tracking starts only after reliable detections.</p><button className="primary">Open evaluation</button></section>
    <section className="grid">{metrics.map(([label, value, detail]) => <article key={label}><p className="eyebrow">{label}</p><strong>{value}</strong><span>{detail}</span></article>)}</section>
    <section className="panel"><div><p className="eyebrow">RECENT RUNS</p><h2>No runs yet</h2><p>Run detector evaluation to see annotated video, precision, recall, and latency.</p></div><button className="secondary">View schema</button></section>
  </main>;
}

createRoot(document.getElementById("root")).render(<App />);
