import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import { cameraAction, createCamera, deleteCamera, editCamera, loadSettings, saveSettings, testCamera, updateSetting, validateSettings } from "./settings";

const label = (value) => value.replaceAll("_", " ");
const emptyCamera = () => ({ id: "", enabled: true, source: { kind: "rtsp", secret_env: "" }, sampling: { queue_size: 2, process_every_n_frames: 1, drop_policy: "drop_oldest" } });

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

function CameraEditor({ camera, editing, busy, result, onChange, onSave, onTest, onCancel }) {
  const source = camera.source || {};
  const setSource = (key, value) => onChange({ ...camera, source: { ...source, [key]: value, ...(value && key === "uri" ? { secret_env: "" } : {}), ...(value && key === "secret_env" ? { uri: "" } : {}) } });
  const setSampling = (key, value) => onChange({ ...camera, sampling: { ...camera.sampling, [key]: value } });
  return <article className="camera-editor"><h2>{editing ? `Edit ${camera.id}` : "Add camera"}</h2>
    <label><span>Camera ID</span><input value={camera.id} disabled={editing} onChange={(event) => onChange({ ...camera, id: event.target.value })} /></label>
    <label><span>Source type</span><select value={source.kind} onChange={(event) => onChange({ ...camera, source: { kind: event.target.value } })}><option value="fake">Fake</option><option value="mp4">MP4</option><option value="rtsp">RTSP</option><option value="http">HTTP / MJPEG</option></select></label>
    {source.kind !== "fake" && <label><span>{source.kind === "mp4" ? "Local path" : "Safe URI"}</span><input value={source.uri || ""} placeholder={source.kind === "mp4" ? "data/videos/sample.mp4" : "No embedded credentials"} onChange={(event) => setSource("uri", event.target.value)} /></label>}
    {(source.kind === "rtsp" || source.kind === "http") && <label><span>Secret environment variable</span><input value={source.secret_env || ""} placeholder="CAMERA_GATE_01_RTSP_URL" onChange={(event) => setSource("secret_env", event.target.value)} /></label>}
    <label><span>Enabled</span><input type="checkbox" checked={Boolean(camera.enabled)} onChange={(event) => onChange({ ...camera, enabled: event.target.checked })} /></label>
    <label><span>Queue size</span><input type="number" min="1" value={camera.sampling?.queue_size ?? 2} onChange={(event) => setSampling("queue_size", Number(event.target.value))} /></label>
    <label><span>Process every N frames</span><input type="number" min="1" value={camera.sampling?.process_every_n_frames ?? 1} onChange={(event) => setSampling("process_every_n_frames", Number(event.target.value))} /></label>
    {result && <p className={result.ok ? "success-inline" : "field-error"}>{result.message}</p>}
    <div className="camera-actions"><button onClick={onTest} disabled={busy || source.kind === "fake"}>Test connection</button><button className="primary" onClick={onSave} disabled={busy}>{busy ? "Working..." : editing ? "Update camera" : "Add camera"}</button>{editing && <button onClick={onCancel}>Cancel</button>}</div>
    <p className="muted">Authenticated network URLs must use a backend environment variable. Credentials never enter browser config.</p>
  </article>;
}

function Settings({ settings, loading, saving, error, saved, onBack, onLoad, onSave, onChange, cameraDraft, editingCamera, cameraBusy, cameraResult, onDraftChange, onEditCamera, onCancelCamera, onSaveCamera, onTestCamera, onDeleteCamera, onToggleCamera, onCameraAction }) {
  const errors = validateSettings(settings || {});
  if (loading) return <section className="panel settings"><p>Loading settings...</p></section>;
  return <section className="settings"><div className="settings-heading"><div><p className="eyebrow">CONFIGURATION</p><h1>Settings</h1><p className="lead">Adjust supported runtime, detection, ownership, alert, and camera values.</p></div><button onClick={onBack}>Back</button></div>{error && <section className="alert">{error}</section>}{saved && <section className="success">Settings saved.</section>}
    <section className="settings-grid"><article><h2>Runtime</h2><NumberField settings={settings} section="runtime" field="max_continuity_gap_seconds" onChange={onChange} /></article><article><h2>Detection</h2><NumberField settings={settings} section="detector" field="confidence" onChange={onChange} readOnly /><NumberField settings={settings} section="detector" field="image_size" onChange={onChange} readOnly /><p className="muted">Detection values are read-only. Current API does not persist detector changes.</p></article><article><h2>Tracking</h2><p className="muted">{settings?.tracker?.backend || "Not configured"}</p><p className="muted">Tracker settings are read-only because current API does not save them.</p></article><article><h2>Ownership</h2><NumberField settings={settings} section="ownership" field="association_seconds" onChange={onChange} /><NumberField settings={settings} section="ownership" field="separation_distance_ratio" onChange={onChange} /></article><article><h2>Separation alerts</h2><NumberField settings={settings} section="alert" field="separation_seconds" onChange={onChange} /><NumberField settings={settings} section="alert" field="stationary_window_seconds" onChange={onChange} /><NumberField settings={settings} section="alert" field="min_stationary_observations" onChange={onChange} /></article></section>
    <section className="camera-management"><CameraEditor camera={cameraDraft} editing={editingCamera} busy={cameraBusy} result={cameraResult} onChange={onDraftChange} onSave={onSaveCamera} onTest={onTestCamera} onCancel={onCancelCamera} /><article><p className="eyebrow">REGISTERED CAMERAS</p>{(settings?.cameras || []).length === 0 && <p className="muted">No cameras configured.</p>}{(settings?.cameras || []).map((camera) => <div className="camera-form" key={camera.id}><h2>{camera.id}</h2><p className="muted">{camera.source?.kind} · {camera.enabled ? "enabled" : "disabled"} · {camera.health?.state || "unknown"} · queue {camera.health?.queue_depth ?? 0} · {camera.health?.processed_fps ?? 0} FPS</p>{camera.health?.last_error && <p className="field-error">{camera.health.last_error}</p>}<div className="camera-actions"><button onClick={() => onEditCamera(camera)}>Edit</button><button onClick={() => onToggleCamera(camera)}>{camera.enabled ? "Disable" : "Enable"}</button><button onClick={() => onCameraAction(camera.id, "start")}>Start</button><button onClick={() => onCameraAction(camera.id, "stop")}>Stop</button><button onClick={() => onCameraAction(camera.id, "reconnect")}>Reconnect</button><button className="danger" onClick={() => onDeleteCamera(camera.id)}>Delete</button></div></div>)}</article></section>
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
  const [cameraDraft, setCameraDraft] = useState(emptyCamera());
  const [editingCamera, setEditingCamera] = useState("");
  const [cameraBusy, setCameraBusy] = useState(false);
  const [cameraResult, setCameraResult] = useState(null);
  const refresh = async () => { setLoading(true); setError(""); try { const responses = await Promise.all([fetch("/api/phase8/cameras"), fetch("/api/events")]); if (responses.some((response) => !response.ok)) throw new Error("Backend unavailable"); setCameras(await responses[0].json()); setEvents(await responses[1].json()); } catch { setError("Backend unavailable"); } finally { setLoading(false); } };
  const load = async () => { setSettingsLoading(true); setError(""); setSaved(false); try { setSettings(await loadSettings()); } catch { setError("Settings unavailable"); } finally { setSettingsLoading(false); } };
  useEffect(() => { refresh(); }, []);
  const openSettings = () => { setView("settings"); load(); };
  const onSave = async () => { setSaving(true); setError(""); setSaved(false); try { await saveSettings(settings); setSaved(true); await refresh(); } catch (saveError) { setError(saveError.message || "Settings save failed"); } finally { setSaving(false); } };
  const cameraPayload = () => ({ ...cameraDraft, source: Object.fromEntries(Object.entries(cameraDraft.source || {}).filter(([, value]) => value !== "" && value != null)), health: undefined });
  const resetCamera = () => { setCameraDraft(emptyCamera()); setEditingCamera(""); setCameraResult(null); };
  const saveCamera = async () => { setCameraBusy(true); setCameraResult(null); setError(""); try { if (editingCamera) await editCamera(editingCamera, cameraPayload()); else await createCamera(cameraPayload()); resetCamera(); await load(); await refresh(); } catch (cameraError) { setError(cameraError.message); } finally { setCameraBusy(false); } };
  const checkCamera = async () => { setCameraBusy(true); setCameraResult(null); try { const result = await testCamera(cameraPayload()); setCameraResult({ ok: true, message: `Connected${result.width ? ` · ${result.width}×${result.height}` : ""} · ${result.latency_ms} ms` }); } catch (cameraError) { setCameraResult({ ok: false, message: cameraError.message }); } finally { setCameraBusy(false); } };
  const removeCamera = async (cameraId) => { if (!window.confirm(`Delete camera ${cameraId}? Stored events and evidence remain.`)) return; setCameraBusy(true); setError(""); try { await deleteCamera(cameraId); if (editingCamera === cameraId) resetCamera(); await load(); await refresh(); } catch (cameraError) { setError(cameraError.message); } finally { setCameraBusy(false); } };
  const runCameraAction = async (cameraId, action) => { setCameraBusy(true); setError(""); try { await cameraAction(cameraId, action); await load(); await refresh(); } catch (cameraError) { setError(cameraError.message); } finally { setCameraBusy(false); } };
  const toggleCamera = async (camera) => { setCameraBusy(true); setError(""); try { const { health, ...configuration } = camera; await editCamera(camera.id, { ...configuration, enabled: !camera.enabled }); await load(); await refresh(); } catch (cameraError) { setError(cameraError.message); } finally { setCameraBusy(false); } };
  return <main><nav><span className="brand">AVP</span><span className="mono">OPERATIONS</span><button onClick={openSettings}>Settings</button></nav>{view === "settings" ? <Settings settings={settings || {}} loading={settingsLoading} saving={saving} error={error} saved={saved} onBack={() => { setView("dashboard"); setError(""); }} onLoad={load} onSave={onSave} onChange={(section, field, value) => setSettings((current) => updateSetting(current, section, field, value))} cameraDraft={cameraDraft} editingCamera={editingCamera} cameraBusy={cameraBusy} cameraResult={cameraResult} onDraftChange={setCameraDraft} onEditCamera={(camera) => { setEditingCamera(camera.id); setCameraDraft({ ...camera, health: undefined }); setCameraResult(null); }} onCancelCamera={resetCamera} onSaveCamera={saveCamera} onTestCamera={checkCamera} onDeleteCamera={removeCamera} onToggleCamera={toggleCamera} onCameraAction={runCameraAction} /> : <Dashboard cameras={cameras} events={events} loading={loading} error={error} refresh={refresh} openSettings={openSettings} />}</main>;
}

createRoot(document.getElementById("root")).render(<App />);
