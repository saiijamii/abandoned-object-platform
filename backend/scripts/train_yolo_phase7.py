import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune Ultralytics YOLO for Phase Seven.")
    parser.add_argument("--data", required=True)
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--imgsz", type=int, default=960)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--project", default="runs/phase7")
    args = parser.parse_args()
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit("Install YOLO dependencies from backend/requirements-phase7.txt") from exc
    YOLO(args.model).train(data=args.data, epochs=args.epochs, imgsz=args.imgsz, device=args.device, project=args.project, name="yolo_finetune")


if __name__ == "__main__":
    main()
