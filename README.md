# Meetmind-AI

A local-first meeting intelligence application that converts recordings into
transcripts, summaries, decisions, and action items. Ask MeetMind uses semantic
retrieval and returns timestamped sources that open the supporting audio.

## Local AI models

MeetMind uses Ollama for structured meeting analysis and embeddings:

```powershell
ollama pull qwen3:1.7b
ollama pull embeddinggemma
```

The embedding model can be changed with the
`OLLAMA_EMBEDDING_MODEL` environment variable. Existing meetings are indexed
automatically when they receive their first question.

## Run the backend

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

## Run the frontend

```powershell
cd frontend
npm install
npm run dev
```

## Tests

```powershell
pytest
cd frontend
npm test
```

Run the small semantic-retrieval evaluation with Ollama running:

```powershell
python -m backend.evaluation.evaluate_retrieval
```

