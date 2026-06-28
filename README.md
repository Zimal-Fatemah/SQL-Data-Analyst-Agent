[README.md](https://github.com/user-attachments/files/29434171/README.md)
<p align="center">
  <h1 align="center"> NL2SQL Data Analyst</h1>
  <p align="center">A production-grade Natural Language → SQL agent with strict structured output.</p>
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python"></a>
  <a href="#"><img src="https://img.shields.io/badge/LangGraph-1.2+-green.svg" alt="LangGraph"></a>
  <a href="#"><img src="https://img.shields.io/badge/Groq-llama--3.3--70b-orange.svg" alt="Groq"></a>
  <a href="#"><img src="https://img.shields.io/badge/License-MIT-lightgrey.svg" alt="License"></a>
</p>

---

## 📋 Table of Contents

- [The Problem](#the-problem)
- [The Solution: Data Sandwich Architecture](#the-solution-data-sandwich-architecture)
- [How It Works](#how-it-works)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Security](#security)
- [Evaluation](#evaluation)
- [Tech Stack](#tech-stack)
- [License](#license)

---

## The Problem

Most NL2SQL agents return freeform prose:

> *"Based on the data, it seems like customers in São Paulo are quite active, and you might want to consider..."*

This is **unusable for automation**. You can't pipe it into a dashboard, trigger a webhook, or validate it programmatically.

---

## The Solution: Data Sandwich Architecture

Every response is forced into a rigid **Pydantic schema** — no hallucinations, no fluff, no markdown violations.

```
┌─────────────────────────────────────────┐
│  🪝 THE HOOK                            │  ← Executive headline (10-15 words)
│  "São Paulo drives 42% of all orders"   │
├─────────────────────────────────────────┤
│  📊 THE TRUTH                           │  ← Raw Markdown data table
│  | state | orders | pct |              │
│  | SP    | 41,746 | 42% |              │
│  | RJ    | 12,853 | 13% |              │
├─────────────────────────────────────────┤
│  🎯 THE STRATEGY                        │  ← Exactly 2 actionable takeaways
│  • Expand warehouse capacity in SP      │
│  • Launch targeted ads in RJ            │
└─────────────────────────────────────────┘
```

**Why this matters:**
- ✅ Machine-readable by default
- ✅ Prevents LLM hallucination via schema enforcement
- ✅ Audit trail (`sql_query_used` is always included)
- ✅ Works with Slack, email, BI dashboards, and downstream agents
<img width="1288" height="817" alt="image" src="https://github.com/user-attachments/assets/b803597c-b297-406d-ab3a-f2b96f73a277" />

---

## How It Works

### Dual-Engine Architecture

We use **two specialized LLM instances** instead of one generalist:

| Engine | Role | Mode | Why |
|--------|------|------|-----|
| **Reasoning Engine** | Generates SQL from natural language | Tool-calling (`bind_tools`) | Needs to "see" the database schema and emit `run_sql_query` calls |
| **Synthesis Engine** | Converts SQL + results into structured JSON | JSON mode (`response_format: json_object`) | Must output valid JSON that validates against `AnalystResponse` |

This separation prevents the model from confusing SQL syntax with JSON formatting.

### LangGraph Workflow

```
┌─────────────┐     ┌─────────────────┐     ┌──────────┐     ┌─────────────────┐
│   START     │────▶│ groq_reasoning  │────▶│  tools   │────▶│ groq_synthesis  │
└─────────────┘     │  (SQL generation)│     │(execute) │     │ (JSON output)   │
                    └─────────────────┘     └──────────┘     └─────────────────┘
                           │                                          │
                           └──────────────────────────────────────────┘
                           (bypass tools if no SQL needed)
                                          │
                                          ▼
                                    ┌──────────┐
                                    │    END   │
                                    └──────────┘
```

### Security-First Design

```python
# OS-level read-only enforcement — not just a flag
db_uri = f"file:{DB_PATH}?mode=ro"
conn = sqlite3.connect(db_uri, uri=True)
```

- **AST-level validation** via `guardrails.py` (rejects `DROP`, `INSERT`, `UPDATE`, `DELETE` before execution)
- **Read-only SQLite URI mode** — the OS blocks writes even if the LLM tries to bypass validation
- **Pandas `read_sql_query`** — results are sanitized into Markdown tables before reaching the LLM

---

## Quick Start

### Prerequisites

- Python 3.10+
- A [Groq](https://groq.com/) API key (free tier available)

### Installation

```bash
git clone https://github.com/Zimal-Fatemah/NL2SQL-data-analyst.git
cd NL2SQL-data-analyst

python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate

pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
groq_api_key=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Run the Agent

```bash
python -m src.agent
```

**Example session:**

```
👤 User: Which 5 cities have the highest number of customers?

🪝 SÃO PAULO LEADS WITH 15,540 CUSTOMERS, FOLLOWED BY RIO DE JANEIRO

| customer_city | customer_count |
|---------------|--------------|
| sao paulo     | 15540        |
| rio de janeiro| 6882         |
| belo horizonte| 2773         |
| brasilia      | 2131         |
| curitiba      | 1521         |

📈 STRATEGIC TAKEAWAYS:
 • Prioritize logistics partnerships in São Paulo and Rio to reduce last-mile delivery costs.
 • Launch localized marketing campaigns in Belo Horizonte and Brasilia to close the gap with top-tier cities.
```

### Run the Evaluation Suite

```bash
python -m eval.run_eval
```

Validates structural correctness against 20 gold-standard questions covering aggregations, joins, time filtering, and comparative analysis.
<img width="1223" height="879" alt="image" src="https://github.com/user-attachments/assets/3371ce1d-b325-4a1c-bcf2-3cd9a61a657a" />

---

## Project Structure

```
NL2SQL-data-analyst/
├── src/
│   ├── agent.py          # LangGraph workflow, Pydantic schemas, CLI
│   ├── tools.py          # DB connection, schema introspection, query execution
│   └── guardrails.py     # AST-based SQL validation (whitelist + DML blocking)
├── eval/
│   ├── qa_set.json       # 20 regression test questions
│   └── run_eval.py       # Automated validation runner
├── db/
│   └── olist.db          # SQLite Olist e-commerce dataset
├── requirements.txt
└── .env.example
```

---

## Security

| Layer | Implementation |
|-------|---------------|
| **Input Validation** | `sqlglot` AST parsing — rejects non-`SELECT` statements |
| **OS Enforcement** | SQLite `?mode=ro` URI flag |
| **Output Sanitization** | Pandas `to_markdown()` prevents HTML/JS injection |
| **Schema Enforcement** | Pydantic `AnalystResponse` — invalid JSON is discarded |

---

## Evaluation

The `eval/` suite checks **structural integrity** (Pydantic validation) across 20 representative queries:

- `COUNT`, `SUM`, `AVG` aggregations
- `GROUP BY` + `ORDER BY` + `LIMIT`
- Date filtering (`2017`, `2018`)
- Multi-table implicit joins
- Comparative metrics (`on time vs late`)

> **Note:** The current suite validates that the agent returns well-formed JSON. Semantic correctness ("did the SQL actually answer the question?") requires human review or a gold-standard result set.

---

## Tech Stack

- **Orchestration:** LangGraph 1.2+
- **LLM:** Groq API (`llama-3.3-70b-versatile`)
- **Validation:** Pydantic 2.x, `sqlglot`
- **Database:** SQLite (read-only URI mode)
- **Data Processing:** Pandas 3.x

---

## License

MIT

---

<p align="center">
  Built with 🥪 by <a href="https://github.com/Zimal-Fatemah">Zimal Fatemah</a>
</p>
