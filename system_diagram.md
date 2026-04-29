# Music Recommender — RAG System Diagram

```mermaid
flowchart TD
    USER_IN["👤 User\nnatural language query\ne.g. 'something chill to study to'"]

    GUARDRAIL_IN["Input Guardrail\n• reject empty / too-long input\n• strip unsafe characters"]

    RETRIEVAL["Retrieval Engine\nsongs.csv  ←  knowledge base\nscore every song against query\nreturn top-k candidates"]

    CONTEXT["Context Builder\nformat retrieved songs\nas structured LLM prompt context"]

    LLM["Claude LLM  (RAG)\nprompt = user query\n       + retrieved song data\nmodel must cite & reason\nover the retrieved context"]

    GUARDRAIL_OUT["Output Guardrail\n• response mentions ≥1 song title\n• response is not empty\n• no obvious hallucinated titles"]

    LOGGER["Logger\nappend to rag_log.jsonl\n  • timestamp\n  • query\n  • retrieved songs\n  • AI response\n  • guardrail result"]

    USER_OUT["👤 User\nrecommendation + explanation\nin natural language"]

    ERR["⚠ Error / Fallback\nlog issue, return safe message"]

    USER_IN --> GUARDRAIL_IN
    GUARDRAIL_IN -- valid --> RETRIEVAL
    GUARDRAIL_IN -- invalid --> ERR

    RETRIEVAL --> CONTEXT
    CONTEXT --> LLM
    LLM --> GUARDRAIL_OUT

    GUARDRAIL_OUT -- passes --> LOGGER
    GUARDRAIL_OUT -- fails --> ERR

    LOGGER --> USER_OUT
    ERR --> USER_OUT

    subgraph TESTING ["🧪 Testing & Human Checks"]
        T1["pytest — unit tests\n(test_recommender.py)\nverify retrieval scores"]
        T2["Consistency test\nrun same query twice\nassert responses are stable"]
        T3["👤 Human review\nspot-check that AI explanation\nactively uses song attributes,\nnot a generic answer"]
    end

    RETRIEVAL -. "tested by" .-> T1
    LLM       -. "tested by" .-> T2
    USER_OUT  -. "reviewed by" .-> T3
```
### Screenshot

<img src="assets/system-diagram.png">


## Component Summary

| Component | Role |
|---|---|
| **Input Guardrail** | Reject bad queries before they reach the LLM |
| **Retrieval Engine** | Score `songs.csv` against the query; return top-k candidates |
| **Context Builder** | Format retrieved songs into a structured prompt block |
| **Claude LLM** | Generate a recommendation that *reasons over* the retrieved data |
| **Output Guardrail** | Verify the response cites real songs and is not empty/hallucinated |
| **Logger** | Write every request + response to `rag_log.jsonl` for audit/debug |

## Data Flow

1. User types a free-text query
2. Input guardrail validates it
3. Retrieval engine searches `songs.csv` and returns top-k scored songs
4. Context builder packages those songs into a prompt
5. Claude receives `[query + retrieved context]` and must reason over it
6. Output guardrail checks the response is grounded in real songs
7. Logger records everything; user sees the final recommendation

## Human & Testing Touchpoints

- **pytest** — unit-tests the retrieval scoring logic (deterministic, no LLM calls)
- **Consistency test** — runs the same query twice and checks the AI gives a stable answer
- **Human review** — spot-check that Claude's explanation references actual song attributes, not a boilerplate response
