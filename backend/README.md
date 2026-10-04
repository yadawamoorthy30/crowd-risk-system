# Crowd Risk System: Backend

Real-Time Crowd Density and Flow-Based Risk Prediction System for Mass Gatherings.

## Setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

1. Create a MySQL database named `crowd_risk`.
2. Copy `.env.example` to `.env` and fill in your MySQL credentials.
3. Apply migrations: `alembic upgrade head`
4. Run the server: `uvicorn app.main:app --reload`

API docs: http://127.0.0.1:8000/docs

## Detection (Phase 2)

Download the model once (about 5 MB):

```powershell
python -c "from ultralytics import YOLO; YOLO('models/yolo26n.pt')"
```

Visual test with the OpenCV window:

```powershell
python scripts\run_vision.py --source 0
python scripts\run_vision.py --imgsz 960
```

API: `POST /api/detection/start`, `POST /api/detection/stop`, `GET /api/detection/status`,
`GET /api/detection/results/{camera_id}`, `GET /api/detection/history/{camera_id}`.