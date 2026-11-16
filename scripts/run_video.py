"""Video CLI entry point reserved for model-enabled runs."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase One detector over a video.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--manifest", default="storage/runs/phase1.json")
    args = parser.parse_args()
    from app.core.config import load_config
    from app.detection.registry import create_detector
    from app.video import process_video

    result = process_video(args.input, args.output, create_detector(load_config(args.config)), args.manifest)
    print(result)


if __name__ == "__main__":
    main()
