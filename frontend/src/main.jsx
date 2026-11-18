import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import { loadSettings, saveSettings, updateCamera, updateSetting, validateSettings } from "./settings";

const label = (value) => value.replaceAll("_", " ");

function Dashboard({ cameras, events, loading, error, refresh, openSettings }) {
  return <>
    <section className="hero"><p className="eyebrow">ABANDONED-OBJECT PLATFORM</p><h1>Camera runtime.<br />Operator clarity.</h1><p className="lead">Multi-camera health, bounded frame processing, and evidence events in one view.</p><button className="primary" onClick={refresh} disabled={loading}>{loading ? "Refreshing..." : "Refresh status"}</button></section>
    {error && <section className="alert">{error}</section>}
    <section className="grid"><article><p className="eyebrow">CAMERAS</p><strong>{cameras.length}</strong><span>runtime sources</span></article><article><p className="eyebrow">RUNTIME</p><strong>{cameras.some((camera) => camera.state === "connected") ? "LIVE" : cameras.length ? "READY" : "—"}</strong><span>fair scheduler</span></article><article><p className="eyebrow">SEARCH</p><strong>RESERVED</strong><span>future capability</span></article></section>
    <section className="panel"><div><p className="eyebrow">CAMERA REGISTRY</p><h2>{cameras.length ? "Camera health" : "No cameras configured"}</h2>{cameras.map((camera) => <p className="camera" key={camera.camera_id}><b>{camera.camera_id}</b><span>{camera.source_type} · {camera.state} · queue {camera.queue_depth}</span></p>)}</div><button className="secondary" onClick={refresh} disabled={loading}>{loading ? "Refreshing..." : "Refresh API"}</button></section>
    <section className="panel"><div><p className="eyebrow">EVENT TIMELINE</p><h2>{events.length ? `${events.length} candidate event${events.length === 1 ? "" : "s"}` : "No events yet"}</h2>{events.slice(0, 5).map((event) => <p className="camera" key={event.event_id}><b>{event.event_type}</b><span>{event.camera_id} · {Number(event.timestamp_s || 0).toFixed(2)}s</span></p>)}</div></section>
    <button className="settings-link" onClick={openSettings}>Open settings</button>
  </>;
}

function NumberField({ settings, section, field, onChange, readOnly = false }) {
  const value = settings?.[section]?.[field];
  return <label><span>{label(field)}</span><input type="number" value={value ?? ""} readOnly={readOnly} onChange={(event) => onChange(section, field, event.target.value)} /></label>;
}

function Settings({ settings, loading, saving, error, saved, onBack, onLoad, onSave, onChange, onCameraChange }) {
  const errors = validateSettings(settings || {});
  if (loading) return <section className="panel settings"><p>Loading settings...</p></section>;
  return <section className="settings"><div className="settings-heading"><div><p className="eyebrow">CONFIGURATION</p><h1>Settings</h1><p className="lead">Adjust supported runtime, detection, ownership, alert, and camera values.</p></div><button onClick={onBack}>Back</button></div>{error && <section className="alert">{error}</section>}{saved && <section className="success">Settings saved.</section>}
    <section className="settings-grid"><article><h2>Runtime</h2><NumberField settings={settings} section="runtime" field="max_continuity_gap_seconds" onChange={onChange} /></article><article><h2>Detection</h2><NumberField settings={settings} section="detector" field="confidence" onChange={onChange} readOnly /><NumberField settings={settings} section="detector" field="image_size" onChange={onChange} readOnly /><p className="muted">Detection values are read-only. Current API does not persist detector changes.</p></article><article><h2>Tracking</h2><p className="muted">{settings?.tracker?.backend || "Not configured"}</p><p className="muted">Tracker settings are read-only because current API does not save them.</p></article><article><h2>Ownership</h2><NumberField settings={settings} section="ownership" field="association_seconds" onChange={onChange} /><NumberField settings={settings} section="ownership" field="separation_distance_ratio" onChange={onChange} /></article><article><h2>Separation alerts</h2><NumberField settings={settings} section="alert" field="separation_seconds" onChange={onChange} /><NumberField settings={settings} section="alert" field="stationary_window_seconds" onChange={onChange} /><NumberField settings={settings} section="alert" field="min_stationary_observations" onChange={onChange} /></article></section>
    <section className="panel camera-settings"><div><p className="eyebrow">CAMERA CONFIGURATION</p>{(settings?.cameras || []).map((camera) => <div className="camera-form" key={camera.id}><h2>{camera.id}</h2><label><span>Enabled</span><input type="checkbox" checked={Boolean(camera.enabled)} onChange={(event) => onCameraChange(camera.id, "enabled", event.target.checked)} /></label><label><span>Queue size</span><input type="number" min="1" value={camera.sampling?.queue_size ?? 1} onChange={(event) => onCameraChange(camera.id, "sampling", { ...camera.sampling, queue_size: event.target.value })} /></label><label><span>Process every N frames</span><input type="number" min="1" value={camera.sampling?.process_every_n_frames ?? 1} onChange={(event) => onCameraChange(camera.id, "sampling", { ...camera.sampling, process_every_n_frames: event.target.value })} /></label><p className="muted">Source credentials hidden. State: {camera.health?.state || "unknown"}.</p>{errors[`camera.${camera.id}.queue_size`] && <p className="field-error">{errors[`camera.${camera.id}.queue_size`]}</p>}</div>)}</div></section>
    <div className="settings-actions"><button className="secondary" onClick={onLoad}>Reload</button><button className="primary" onClick={onSave} disabled={saving || Object.keys(errors).length}>{saving ? "Saving..." : "Save settings"}</button></div>
  </section>;
}

function App() {
  const [view, setView] = useState("dashboard");
  const [cameras, setCameras] = useState([]);
  const [events, setEvents] = useState([]);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const refresh = async () => { setLoading(true); setError(""); try { const responses = await Promise.all([fetch("/api/phase8/cameras"), fetch("/api/events")]); if (responses.some((response) => !response.ok)) throw new Error("Backend unavailable"); setCameras(await responses[0].json()); setEvents(await responses[1].json()); } catch { setError("Backend unavailable"); } finally { setLoading(false); } };
  const load = async () => { setSettingsLoading(true); setError(""); setSaved(false); try { setSettings(await loadSettings()); } catch { setError("Settings unavailable"); } finally { setSettingsLoading(false); } };
  useEffect(() => { refresh(); }, []);
  const openSettings = () => { setView("settings"); load(); };
  const onSave = async () => { setSaving(true); setError(""); setSaved(false); try { await saveSettings(settings); setSaved(true); await refresh(); } catch (saveError) { setError(saveError.message || "Settings save failed"); } finally { setSaving(false); } };
  return <main><nav><span className="brand">AVP</span><span className="mono">OPERATIONS</span><button onClick={openSettings}>Settings</button></nav>{view === "settings" ? <Settings settings={settings || {}} loading={settingsLoading} saving={saving} error={error} saved={saved} onBack={() => { setView("dashboard"); setError(""); }} onLoad={load} onSave={onSave} onChange={(section, field, value) => setSettings((current) => updateSetting(current, section, field, value))} onCameraChange={(cameraId, key, value) => setSettings((current) => updateCamera(current, cameraId, key, value))} /> : <Dashboard cameras={cameras} events={events} loading={loading} error={error} refresh={refresh} openSettings={openSettings} />}</main>;
}

createRoot(document.getElementById("root")).render(<App />);
