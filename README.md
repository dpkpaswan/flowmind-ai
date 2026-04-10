# FlowMind AI — Predictive Crowd Intelligence for Stadiums

> AI-powered crowd prediction, wait time estimation, and smart navigation for large sports stadiums.

---

## Tech Stack

| Layer       | Technology              |
|-------------|-------------------------|
| Backend     | FastAPI (Python)        |
| Frontend    | React + Vite            |
| AI          | Google Gemini Flash API |
| Database    | Firebase Realtime DB (mock) |
| Deployment  | Docker + Cloud Run      |

---

## Project Structure

```
PromptWars/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py             # App entry point
│   │   ├── config.py           # Settings & environment
│   │   ├── routers/            # API endpoints
│   │   │   ├── crowd.py        # Crowd density & predictions
│   │   │   ├── wait_times.py   # Facility wait times
│   │   │   ├── alerts.py       # Smart alerts
│   │   │   └── chat.py         # AI chat assistant
│   │   ├── services/           # Business logic
│   │   │   ├── crowd_service.py
│   │   │   ├── wait_service.py
│   │   │   ├── alert_service.py
│   │   │   └── gemini_service.py
│   │   ├── models/
│   │   │   └── schemas.py      # Pydantic models
│   │   ├── data/
│   │   │   ├── mock_generator.py   # Stadium simulation
│   │   │   └── firebase_client.py  # In-memory mock DB
│   │   └── utils/
│   │       └── helpers.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env
├── frontend/                   # React + Vite frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard/      # Overview stats + zone grid
│   │   │   ├── Heatmap/        # Stadium density map
│   │   │   ├── WaitTimes/      # Facility wait cards
│   │   │   ├── Alerts/         # Smart alert feed
│   │   │   ├── Chat/           # AI assistant chat
│   │   │   └── Layout/         # Sidebar + Header
│   │   ├── services/api.js     # API client
│   │   ├── hooks/usePolling.js # Auto-refresh hook
│   │   └── utils/constants.js
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── README.md                   # ← You are here
```

---

## Quick Start

### Prerequisites

- **Python 3.10+** installed
- **Node.js 18+** and **npm** installed
- (Optional) A **Gemini API key** from [Google AI Studio](https://aistudio.google.com/apikey)

### 1. Start the Backend

```bash
# Open a terminal and navigate to the backend folder
cd backend

# Install Python dependencies
pip install -r requirements.txt

# (Optional) Add your Gemini API key to .env
# Open .env and set: GEMINI_API_KEY=your-key-here
# If you skip this, the AI chat will use a smart rule-based fallback.

# Start the FastAPI server
python -m uvicorn app.main:app --reload --port 8000
```

You should see:
```
[STADIUM] FlowMind AI v1.0.0 starting up...
[DATA] Initial stadium data generated.
[READY] Docs at http://localhost:8000/docs
```

**Verify:** Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser to see the Swagger API docs.

### 2. Start the Frontend

```bash
# Open a SECOND terminal and navigate to the frontend folder
cd frontend

# Install Node dependencies
npm install

# Start the Vite dev server
npm run dev
```

You should see:
```
VITE v8.x.x  ready in ~1s

  ➜  Local:   http://localhost:5173/
```

**Open:** [http://localhost:5173](http://localhost:5173) in your browser.

---

## Features

### 1. Dashboard
- Live attendance counter and overall density percentage
- Zone-by-zone density cards with color-coded status (Low / Moderate / High / Critical)
- Density bars with 15-minute prediction markers
- Average wait times for food, restrooms, and gates

### 2. Crowd Heatmap
- Interactive stadium layout showing all 4 main stands
- Click any zone to see 5/10/15 minute density predictions
- Color-coded density visualization (green → yellow → orange → red)
- Side panel for Food Courts, Main Gate, and VIP Lounge

### 3. Wait Times
- Filter by facility type: Food Stalls, Restrooms, Gates
- Each card shows current wait, queue length, and predicted trend
- **Best Pick** banner recommends the shortest-wait option with reasoning
- Color-coded wait bars (green < 5m, blue < 10m, amber < 20m, red 20m+)

### 4. Smart Alerts
- Real-time alerts generated from crowd density and wait time thresholds
- Three severity levels: Critical, Warning, Info
- Each alert includes an **actionable recommendation**
- Alert count badges for quick severity overview

### 5. AI Assistant
- Chat with FlowMind AI about the stadium
- The AI receives **live stadium data** (density, wait times, alerts) as context
- Quick-action buttons for common questions
- Decision-focused responses (not generic chatbot answers)
- Works with or without a Gemini API key (rule-based fallback)

---

## API Endpoints

| Method | Endpoint                          | Description                          |
|--------|-----------------------------------|--------------------------------------|
| GET    | `/`                               | Health check + API info              |
| GET    | `/api/crowd/current`              | Current zone densities               |
| GET    | `/api/crowd/predict`              | 5/10/15 min congestion forecasts     |
| GET    | `/api/crowd/heatmap`              | Heatmap data (lat/lng/weight)        |
| GET    | `/api/wait-times`                 | All facility wait times              |
| GET    | `/api/wait-times/best/{type}`     | Best facility recommendation         |
| GET    | `/api/wait-times/{id}/predict`    | Facility-specific prediction         |
| GET    | `/api/alerts`                     | Active smart alerts                  |
| GET    | `/api/alerts/history`             | Recent alert history                 |
| POST   | `/api/chat`                       | AI assistant (body: `{message}`)     |

---

## Gemini AI Setup (Optional)

1. Get a free API key from [Google AI Studio](https://aistudio.google.com/apikey)
2. Open `backend/.env`
3. Set `GEMINI_API_KEY=your-api-key-here`
4. Restart the backend

Without an API key, the chat uses an intelligent **rule-based fallback** that still provides data-driven responses using live stadium data.

---

## How the Mock Data Works

The system simulates a realistic stadium experience:

- **8 zones**: North/South/East/West Stands, Food Court A & B, Main Gate, VIP Lounge
- **13 facilities**: 5 food stalls, 4 restrooms, 4 gates
- **Time-varying density**: Uses sine waves + noise to mimic event flow (buildup → peak → halftime dip → exit surge)
- **20-minute cycle**: The simulation cycles through a compressed match timeline every 20 minutes
- **Background refresh**: Data updates every 30 seconds on the backend
- **Frontend polling**: UI refreshes every 15 seconds

---

## Docker (Production)

```bash
# Backend
cd backend
docker build -t flowmind-backend .
docker run -p 8000:8000 flowmind-backend

# Frontend (build first)
cd frontend
npm run build
```

---

## License

MIT
