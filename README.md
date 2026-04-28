# Country Information AI Agent

A LangGraph-powered AI agent that answers natural language questions about countries using live data from the REST Countries API.


---

## Architecture

```
User Question
     ↓
[ Node 1 — Intent Parse ]
  Extract country + fields using OpenAI structured output
     ↓
[ Node 2 — Fetch Data ]
  Call REST Countries API (restcountries.com)
     ↓
[ Node 3 — Synthesize Answer ]
  Generate clean natural language answer
     ↓
Final Answer
```

The agent is built with **LangGraph** — each step is an isolated node that reads from and writes to a shared `AgentState`. Errors at any node short-circuit the pipeline and flow through to the final answer gracefully.

---

## Agent Flow

### Node 1 — Intent Parse
Takes the user's raw question and uses OpenAI's structured output API to extract:
- `country` — the country being asked about
- `fields` — which data fields are needed (population, capital, currencies, etc.)

If no country is identifiable, an error is set and the pipeline skips to the final node immediately — no wasted API calls.

### Node 2 — Fetch Data
Calls the REST Countries API with the extracted country name. Handles:
- 404 — country not found
- Timeout — request took too long
- Ambiguous matches — prefers exact name match over partial matches

### Node 3 — Synthesize Answer
Passes only the relevant fields (not the full payload) to the LLM and generates a clean, grounded natural language answer. If an error was set upstream, it returns the error message directly without making an LLM call.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent pipeline | LangGraph |
| LLM | OpenAI `gpt-4o-mini` (Responses API) |
| Structured output | Pydantic + OpenAI `responses.parse` |
| Data source | REST Countries API |
| API | FastAPI + uvicorn |
| UI | Plain HTML/JS (chat interface) |

---

## Project Structure

```
country-agent/
├── agent/
│   ├── __init__.py
│   ├── graph.py        # LangGraph nodes + CountryAgent class
│   ├── state.py        # AgentState TypedDict + CountryIntent Pydantic model
│   └── prompts.py      # System prompts for intent + synthesis nodes
├── api/
│   └── app.py          # FastAPI app, routes, middleware
├── static/
│   └── index.html      # Chat UI
├── main.py             # Entry point
└── pyproject.toml
```

---

## Running Locally

### Prerequisites
- Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- OpenAI API key

### Setup

```bash
git clone <your-repo-url>
cd country-agent

uv sync

cp .env.example .env
# Add your OPENAI_API_KEY to .env
```

### Run

```bash
uv run python main.py
```

Open `http://localhost:8081` for the chat UI.  
Open `http://localhost:8081/docs` for the API explorer.

---

## API

### `POST /ask`

```json
// Request
{ "query": "What currency does Japan use?" }

// Response
{
  "answer": "Japan uses the Japanese Yen (JPY), symbolized by ¥.",
  "country": "Japan",
  "fields": ["currencies"],
  "error": null
}
```

### `GET /health`

```json
{ "status": "ok" }
```

---

## Example Questions

| Question | What the agent does |
|----------|-------------------|
| "What is the capital of Brazil?" | Extracts `capital`, fetches Brazil, answers |
| "What currency does Japan use?" | Extracts `currencies`, fetches Japan, answers |
| "Tell me about Germany" | Extracts all fields, gives full summary |
| "What is the capital of Narnia?" | 404 from API → graceful error |
| "asdfghjkl" | No country identified → error, no API call made |

---

## Known Limitations

- **No conversation memory** — each question is independent
- **English only** — intent parsing and answers are in English only
- **Country name dependent** — ambiguous names (e.g. "Georgia") may return unexpected results
- **Single data source** — missing or outdated fields in REST Countries API cannot be supplemented

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |