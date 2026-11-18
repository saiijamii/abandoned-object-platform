import { describe, expect, it, vi } from "vitest";
import { loadSettings, saveSettings, validateSettings } from "./settings";

describe("settings", () => {
  it("validates numeric settings and camera queue", () => {
    expect(Object.keys(validateSettings({ runtime: { max_continuity_gap_seconds: -1 }, cameras: [{ id: "cam", sampling: { queue_size: 0 } }] }))).toEqual([
      "runtime.max_continuity_gap_seconds",
      "camera.cam.queue_size",
    ]);
  });

  it("loads config and joins camera health", async () => {
    const fetcher = vi.fn((path) => Promise.resolve({ ok: true, json: async () => path === "/api/config" ? { cameras: [{ id: "cam", enabled: true }] } : [{ camera_id: "cam", state: "connected" }] }));
    await expect(loadSettings(fetcher)).resolves.toEqual({ cameras: [{ id: "cam", enabled: true, health: { camera_id: "cam", state: "connected" } }] });
  });

  it("saves only supported settings and cameras", async () => {
    const fetcher = vi.fn(() => Promise.resolve({ ok: true, json: async () => ({ saved: true }) }));
    await expect(saveSettings({ runtime: {}, ownership: {}, alert: {}, detector: { secret: "no" }, cameras: [{ id: "cam", enabled: true, sampling: { queue_size: 2 } }] }, fetcher)).resolves.toEqual({ saved: true });
    expect(fetcher.mock.calls[0][0]).toBe("/api/config");
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).not.toHaveProperty("detector");
  });
});
