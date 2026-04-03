# DriverX Chatbot

A full DriverX chatbot project built with:
- FastAPI backend (intent-based chatbot API)
- React + Vite frontend (modern chatbot UI)

## Project Structure

- `backend/app.py` - FastAPI app with `/chat` and `/health`
- `backend/requirements.txt` - backend dependencies
- `data/knowledge.json` - DriverX support intents and responses
- `frontend/` - React chatbot UI

## Run Backend

```bash
cd backend
pip install -r requirements.txt
cd ..
uvicorn backend.app:app --reload --port 8000
```

## Run Frontend

```bash
cd frontend
npm install
npm run dev
```

By default, frontend uses:
- `http://localhost:8000` when running locally
- `window.location.origin` in production

If needed, set `VITE_API_BASE` in frontend environment.

## Build Frontend

```bash
cd frontend
npm run build
npm run preview
```

## Docker (Backend)

```bash
docker build -t driverx-chatbot .
docker run -p 8000:8000 driverx-chatbot
```


