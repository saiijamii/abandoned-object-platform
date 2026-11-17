# Phase Three checkpoint

Implemented:

- real detector-to-BoxMOT runner
- source-video timestamp processing
- annotated MP4 output at source FPS
- track-history persistence
- ownership, separation, stationarity, and evidence integration
- detector/tracker timing metrics
- CSV recall evaluator

Acceptance status: pending local MP4, model weights, BoxMOT, codec, and ground-truth annotations.

Do not report green-duffel recall from detection frame rate. Use annotated ground truth with `scripts/evaluate_recall.py`.
