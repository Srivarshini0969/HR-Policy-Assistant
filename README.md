# HR Policy Assistant — Ollama, Qwen, Flask and TF-IDF

## Important
The bundled `data/hr_policies_demo.txt` contains **fictional demonstration policies**, not a real company's HR rules. Replace or supplement it only with authorized policy documents before using this for real policies.

## Stack
- Python + Flask web app
- scikit-learn TF-IDF and cosine similarity retrieval
- Local Ollama API with Qwen (`qwen2.5:3b` by default)
- HTML/CSS/JavaScript UI
- pytest tests

## Prerequisites
1. Install Python (Python 3.10+ recommended).
2. Install Ollama from https://ollama.com
3. Download the model: `ollama pull qwen2.5:3b`

## Windows setup (VS Code terminal)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
ollama pull qwen2.5:3b
```

If PowerShell blocks activation, use this only for the current terminal:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Run
Ensure Ollama is running, then:
```powershell
python app.py
```
Open http://127.0.0.1:5000

## Test
```powershell
python -m pytest -v
```
Tests mock the model for relevant checks and do not prove live Qwen response quality.

## Add policies
Put UTF-8 `.txt` policy files in `data/`, one policy paragraph per section. Restart the Flask application or call `POST /api/reindex` to rebuild the index. Do not place secrets or personal employee records in demo documents.

## Behavior and limitations
- TF-IDF retrieves text based on lexical similarity; it is not semantic retrieval.
- The similarity threshold is a heuristic and must be evaluated on a real test set.
- Some sensitive topics are routed to HR; keyword checks are only a basic safeguard.
- The model is instructed to answer only from retrieved text, but this does not guarantee factual correctness.
- Validate every output and source against the official policy.
- The app is an academic prototype, not a production HR system.
- Live answer generation requires Ollama to be running and the configured model to be installed.
- `evaluation.csv` lists test cases as NOT RUN until a person or test harness records actual outcomes.
