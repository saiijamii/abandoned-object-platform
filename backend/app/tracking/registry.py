from .boxmot_adapter import BoxMOTTracker, TrackerConfig


def create_tracker(camera_id: str, session_id: str, config: dict) -> BoxMOTTracker:
    values = config.get("tracker", config)
    return BoxMOTTracker(camera_id, session_id, TrackerConfig(
        backend=values.get("backend", "bytetrack"),
        max_lost_frames=int(values.get("max_lost_frames", 30)),
        use_embeddings=bool(values.get("use_embeddings", False)),
        use_cmc=bool(values.get("use_cmc", False)),
    ))
