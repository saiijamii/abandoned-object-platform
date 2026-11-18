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
  const [configResponse, camerasResponse] = await Promise.all([fetcher("/api/config"), fetcher("/api/phase8/cameras")]);
  if (!configResponse.ok || !camerasResponse.ok) throw new Error("Settings unavailable");
  const config = await configResponse.json();
  const health = await camerasResponse.json();
  const healthById = Object.fromEntries(health.map((camera) => [camera.camera_id, camera]));
  return { ...config, cameras: (config.cameras || []).map((camera) => ({ ...camera, health: healthById[camera.id] || null })) };
}

export async function saveSettings(settings, fetcher = fetch) {
  const errors = validateSettings(settings);
  if (Object.keys(errors).length) throw new Error(Object.values(errors)[0]);
  const response = await fetcher("/api/config", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
    runtime: settings.runtime,
    ownership: settings.ownership,
    alert: settings.alert,
    cameras: (settings.cameras || []).map(({ id, enabled, sampling, reconnect }) => ({ id, enabled, sampling, reconnect })),
  }) });
  if (!response.ok) throw new Error("Settings save failed");
  return response.json();
}
