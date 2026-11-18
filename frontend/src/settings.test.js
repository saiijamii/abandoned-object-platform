import { describe, expect, it, vi } from "vitest";
import { cameraAction, createCamera, deleteCamera, loadSettings, saveSettings, testCamera, validateSettings } from "./settings";

describe("settings", () => {
  it("validates numeric settings and camera queue", () => {
    expect(Object.keys(validateSettings({ runtime: { max_continuity_gap_seconds: -1 }, cameras: [{ id: "cam", sampling: { queue_size: 0 } }] }))).toEqual([
      "runtime.max_continuity_gap_seconds",
      "camera.cam.queue_size",
    ]);
  });

  it("loads config and joins camera health", async () => {
    const fetcher = vi.fn((path) => Promise.resolve({ ok: true, json: async () => path === "/api/config" ? { runtime: {} } : [{ id: "cam", enabled: true, health: { camera_id: "cam", state: "connected" } }] }));
    await expect(loadSettings(fetcher)).resolves.toEqual({ runtime: {}, cameras: [{ id: "cam", enabled: true, health: { camera_id: "cam", state: "connected" } }] });
  });

  it("saves only supported global settings", async () => {
    const fetcher = vi.fn(() => Promise.resolve({ ok: true, json: async () => ({ saved: true }) }));
    await expect(saveSettings({ runtime: {}, ownership: {}, alert: {}, detector: { secret: "no" }, cameras: [{ id: "cam", enabled: true, sampling: { queue_size: 2 } }] }, fetcher)).resolves.toEqual({ saved: true });
    expect(fetcher.mock.calls[0][0]).toBe("/api/config");
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).not.toHaveProperty("detector");
  });

  it("uses camera CRUD, test, and runtime endpoints", async () => {
    const fetcher = vi.fn(() => Promise.resolve({ ok: true, json: async () => ({ ok: true }) }));
    await createCamera({ id: "cam" }, fetcher);
    await testCamera({ id: "cam" }, fetcher);
    await cameraAction("cam", "reconnect", fetcher);
    await deleteCamera("cam", fetcher);
    expect(fetcher.mock.calls.map(([path]) => path)).toEqual(["/api/cameras", "/api/cameras/test", "/api/cameras/cam/reconnect", "/api/cameras/cam"]);
  });
});
