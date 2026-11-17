import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.evaluation.event_trace import validate_trace_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Phase Seven ownership event trace.")
    parser.add_argument("--trace", required=True)
    parser.add_argument("--seconds", type=float, default=2.0)
    args = parser.parse_args()
    errors = validate_trace_file(args.trace, args.seconds)
    if errors:
        print("\n".join(errors))
        raise SystemExit(1)
    print("event trace: PASS")


if __name__ == "__main__":
    main()
