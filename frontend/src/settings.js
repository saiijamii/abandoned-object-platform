export function validateSettings(settings) {
  const errors = {};
  const positive = [
    ["runtime", "max_continuity_gap_seconds"],
    ["detector", "confidence"],
    ["detector", "image_size"],
    ["alert", "separation_seconds"],
    ["alert", "stationary_window_seconds"],
    ["alert", "min_stationary_observations"],
  ];
  for (const [section, key] of positive) {
    const value = settings?.[section]?.[key];
    if (value !== undefined && (!Number.isFinite(Number(value)) || Number(value) < 0)) errors[`${section}.${key}`] = "Enter a non-negative number";
  }
  for (const camera of settings?.cameras || []) {
    const queueSize = Number(camera?.sampling?.queue_size);
    if (!Number.isInteger(queueSize) || queueSize < 1) errors[`camera.${camera.id}.queue_size`] = "Queue size must be positive";
  }
  return errors;
}

export function updateSetting(settings, section, key, value) {
  return { ...settings, [section]: { ...settings[section], [key]: value } };
}

export function updateCamera(settings, cameraId, key, value) {
  return { ...settings, cameras: (settings.cameras || []).map((camera) => camera.id === cameraId ? { ...camera, [key]: value } : camera) };
}

export async function loadSettings(fetcher = fetch) {
  const [configResponse, camerasResponse] = await Promise.all([fetcher("/api/config"), fetcher("/api/cameras")]);
  if (!configResponse.ok || !camerasResponse.ok) throw new Error("Settings unavailable");
  const config = await configResponse.json();
  return { ...config, cameras: await camerasResponse.json() };
}

export async function saveSettings(settings, fetcher = fetch) {
  const errors = validateSettings(settings);
  if (Object.keys(errors).length) throw new Error(Object.values(errors)[0]);
  const response = await fetcher("/api/config", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
    runtime: settings.runtime,
    ownership: settings.ownership,
    alert: settings.alert,
  }) });
  if (!response.ok) throw new Error("Settings save failed");
  return response.json();
}

export async function createCamera(camera, fetcher = fetch) {
  return cameraRequest("/api/cameras", "POST", camera, fetcher);
}

export async function editCamera(cameraId, camera, fetcher = fetch) {
  return cameraRequest(`/api/cameras/${encodeURIComponent(cameraId)}`, "PUT", camera, fetcher);
}

export async function testCamera(camera, fetcher = fetch) {
  return cameraRequest("/api/cameras/test", "POST", camera, fetcher);
}

export async function deleteCamera(cameraId, fetcher = fetch) {
  const response = await fetcher(`/api/cameras/${encodeURIComponent(cameraId)}`, { method: "DELETE" });
  if (!response.ok) throw new Error(await responseError(response, "Camera delete failed"));
  return response.json();
}

export async function cameraAction(cameraId, action, fetcher = fetch) {
  const response = await fetcher(`/api/cameras/${encodeURIComponent(cameraId)}/${action}`, { method: "POST" });
  if (!response.ok) throw new Error(await responseError(response, `Camera ${action} failed`));
  return response.json();
}

async function cameraRequest(path, method, camera, fetcher) {
  const response = await fetcher(path, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(camera) });
  if (!response.ok) throw new Error(await responseError(response, "Camera request failed"));
  return response.json();
}

async function responseError(response, fallback) {
  try { return (await response.json()).detail || fallback; } catch { return fallback; }
}
