import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune RF-DETR for Phase Seven.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--output", default="runs/phase7/rfdetr")
    args = parser.parse_args()
    try:
        from rfdetr import RFDETRNano
    except ImportError as exc:
        raise SystemExit("Install RF-DETR training dependencies from backend/requirements-phase7.txt") from exc
    RFDETRNano().train(dataset_dir=args.dataset, epochs=args.epochs, output_dir=args.output)


if __name__ == "__main__":
    main()
