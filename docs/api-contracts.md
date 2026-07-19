# API Contracts

Cross-team HTTP contracts for StudyMind. Team Mu owns the chatbot RAG service;
Team Pluto (Web) will call it from the frontend.

---

## Chatbot RAG API (Team Mu)

**Service root:** `chatbot/rag-engine/` (separate from `web/backend/`)

**Default local base URL:** `http://127.0.0.1:8001`

**Run:**

```bash
cd chatbot
pip install -r requirements.txt
cd rag-engine
uvicorn main:app --reload --host 127.0.0.1 --port 8001
```

Interactive docs: [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)

Env vars: see `chatbot/rag-engine/.env.example` (`GROQ_API_KEY`, optional `DEFAULT_TOP_K`, `MAX_DISTANCE`, `ENABLE_RERANK`, `ENABLE_MULTI_HOP`, `MAX_RETRIEVAL_ROUNDS`, `CORS_ORIGINS`).

**Pipeline (Phase 6):** query rewrite (when history) → agentic multi-hop retrieve (max 3) → optional re-rank → relevance gate → answer with **original** question (conflict + injection rules) → grounding check.

Multi-source demo corpus under `chatbot/rag-engine/data/`: PDF overview, YouTube lecture notes, conflict notes, injection sample.

---

### `GET /health`

**Response `200`:**

```json
{
  "status": "ok",
  "chunks_indexed": 12,
  "embedding_model": "all-MiniLM-L6-v2",
  "default_top_k": 4,
  "max_distance": 1.2
}
```

---

### `POST /ask`

#### Request body

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|--------|
| `question` | string | yes | — | Non-empty; original wording used for the final answer |
| `history` | array of `{role, content}` | no | omit | Triggers query rewrite for follow-ups |
| `top_k` | integer | no | `4` | Clamped **1–8** (per hop) |
| `include_sources` | boolean | no | `true` | Rich `sources` objects |
| `rerank` | boolean | no | `true` | LLM re-rank wider pool → `top_k` |
| `multi_hop` | boolean | no | `true` | Allow additional retrieval rounds (max `MAX_RETRIEVAL_ROUNDS`) |

**Example (cross-source compare — often multi-hop):**

```json
{
  "question": "Compare what the PDF textbook says about where the Calvin cycle occurs with what the YouTube lecture says about how ATP is produced in the light reactions.",
  "top_k": 4,
  "multi_hop": true,
  "include_sources": true
}
```

#### Response `200`

| Field | Type | Notes |
|-------|------|--------|
| `answer` | string | Always present |
| `refused` | boolean | Relevance gate failed |
| `top_k` | integer | Per-hop keep count |
| `sources` | array or `null` | Rich attribution when `include_sources` |
| `source_ids` | string[] | e.g. `["pdf_chunk_1","yt_chunk_0"]` |
| `rewritten_question` | string | First-hop search query (after rewrite) |
| `grounded` | boolean or `null` | `null` when refused |
| `retrieval_rounds` | integer | How many retrieval hops ran |
| `hop_queries` | string[] | Every embedded search query in order |
| `conflict_hint` | boolean | `true` when conflict fixture chunks were among sources |

**Source item:** `id`, `distance`, `preview`, `source` (filename).

**Success example:**

```json
{
  "answer": "Your sources cover different aspects... The PDF says the Calvin cycle occurs in the stroma. The YouTube lecture explains ATP is produced via chemiosmosis through ATP synthase...",
  "refused": false,
  "top_k": 4,
  "source_ids": ["pdf_chunk_1", "yt_chunk_0"],
  "rewritten_question": "Compare PDF Calvin cycle location with YouTube ATP production...",
  "grounded": true,
  "retrieval_rounds": 2,
  "hop_queries": [
    "Compare PDF Calvin cycle location with YouTube ATP production...",
    "YouTube lecture ATP synthase proton gradient light reactions"
  ],
  "conflict_hint": false,
  "sources": [
    {
      "id": "pdf_chunk_1",
      "distance": 0.45,
      "preview": "The Calvin cycle takes place in the stroma...",
      "source": "photosynthesis_overview.txt"
    }
  ]
}
```

**Conflict example:** When notes disagree, the answer should explicitly say sources disagree (e.g. Calvin cycle darkness claim).

**Refusal:** `grounded` is `null`; `retrieval_rounds` is typically `1`; `sources` / `source_ids` empty.

Exact refusal string:

```text
I don't have enough information to answer that
```

#### Errors

| Status | When |
|--------|------|
| `400` | Empty / invalid `question` |
| `503` | Engine not ready, or missing `GROQ_API_KEY` when an LLM call is required |

---

## Web backend (Team Pluto)

See `web/backend/` — `GET /health`. Chatbot `/ask` lives only on the Mu service.

---

## Ingestion (Team Lambda)

See `ai-ml/ingestion/`. Extracted document text must be treated as **untrusted data** when fed into RAG (see `docs/architecture.md` — Team Mu RAG security).
