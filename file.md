abandoned-object-platform/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── health.py
│   │   │   │   ├── videos.py
│   │   │   │   ├── events.py
│   │   │   │   └── tracks.py
│   │   │   └── schemas.py
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── logging.py
│   │   │   └── clock.py
│   │   │
│   │   ├── detection/
│   │   │   ├── base.py
│   │   │   ├── types.py
│   │   │   ├── yolo.py
│   │   │   ├── rfdetr.py
│   │   │   └── class_map.py
│   │   │
│   │   ├── tracking/
│   │   │   ├── base.py
│   │   │   ├── bytetrack.py
│   │   │   ├── botsort.py
│   │   │   ├── registry.py
│   │   │   └── types.py
│   │   │
│   │   ├── ownership/
│   │   │   ├── association.py
│   │   │   ├── state_machine.py
│   │   │   └── types.py
│   │   │
│   │   ├── events/
│   │   │   ├── service.py
│   │   │   ├── evidence.py
│   │   │   └── schemas.py
│   │   │
│   │   ├── video/
│   │   │   ├── source.py
│   │   │   ├── file_source.py
│   │   │   ├── processor.py
│   │   │   └── writer.py
│   │   │
│   │   ├── storage/
│   │   │   ├── tracks.py
│   │   │   ├── events.py
│   │   │   └── filesystem.py
│   │   │
│   │   └── main.py
│   │
│   ├── config/
│   │   ├── default.yaml
│   │   └── trackers/
│   │       ├── botsort.yaml
│   │       └── bytetrack.yaml
│   │
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   └── README.md
│
├── data/
│   ├── videos/
│   ├── datasets/
│   └── evaluation/
│
├── storage/
│   ├── events/
│   ├── tracks/
│   └── runs/
│
├── docs/
│   ├── design.md
│   └── phase-checkpoints/
│
├── scripts/
│   ├── evaluate_detector.py
│   ├── extract_frames.py
│   └── run_video.py
│
└── README.md
