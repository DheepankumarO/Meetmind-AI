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

## Speaker diarization

Speaker detection uses the local Pyannote Community-1 model. Install its
optional dependencies:

```powershell
pip install -r backend/requirements-diarization.txt
```

Accept the model conditions at
https://huggingface.co/pyannote/speaker-diarization-community-1, create a
Hugging Face access token, and set it before starting the backend:

```powershell
$env:HUGGINGFACE_TOKEN="hf_your_token"
$env:PYANNOTE_METRICS_ENABLED="0"
```

Without the optional package or token, meetings still process normally and
all transcript lines use the fallback label `Speaker 1`.

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

