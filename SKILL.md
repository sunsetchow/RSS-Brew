---
name: rss-brew
description: Daily AI-powered RSS content aggregator. Fetches feeds, scores articles, translates summaries, and generates markdown digests. Use when asked to "run rss brew", "fetch daily news", or "process feeds".
---

# RSS-Brew Automation (Python Core Pipeline)

This skill runs a daily RSS aggregator.
Because this is a long-running, multi-step pipeline (fetching sources, extracting text, running LLM evaluations, translating, and file generation), **do not run this synchronously in the main thread**.

## Execution Protocol

When triggered, immediately spawn a subagent using `sessions_spawn` with the `SMART` model to run the pipeline asynchronously.

**Subagent Configuration:**
- runtime: `subagent`
- model: `SMART`
- task: "You are the RSS-Brew aggregator. Follow the pipeline described below to fetch today's news, evaluate it, and save the markdown files to ./data/."

---

## The RSS-Brew Pipeline (For the Subagent)

**DATA PATH:** `./data` (or `$RSS_DATA_DIR` if set)

### PHASE 1: FETCH + EXTRACT (Python Core)
Run the core pipeline to fetch feeds, deduplicate, and extract clean article text:

```bash
python ./core_pipeline.py \
  --sources ./data/sources.yaml \
  --dedup ./data/processed-index.json \
  --output ./data/new-articles.json
```

This produces a **clean JSON payload** of *only new* articles at:
`./data/new-articles.json`

### PHASE 2: LOAD NEW ARTICLES
Read `new-articles.json`. If `article_count` is 0, stop early after updating the daily digest (optional) and report no new items.

### PHASE 3: TIER-1 ANALYSIS
For each new article, evaluate and assign a Score.
**Positive factors (+1 each):** First-hand interview, Original analysis, Multi-case compilation, Balanced perspective, Expert author, Exclusive info, >2000 words, >5000 words, Original charts/data, Highly relevant to VC/Startups/MBA, Actionable frameworks.
**Negative factors:** One-sided (-1), Overly technical (-1), Unsubstantiated claims (-1), Product pitch (-2), Pure sales (-3).
Determine: category (AI & Frontier Tech | VC & Investment | Startup Strategy | Business Insights | China Tech & Market | Product & Design | Learning & Career | Productivity & Tools | Strategy & Analysis | Other), english summary (2-4 sentences), chinese summary (2-4 sentences).

### PHASE 4: TIER-2 DEEP ANALYSIS
If **score ≥ 3**, generate: paragraph_summaries, underwater_insights, golden_quotes.

### PHASE 5: GENERATE MARKDOWN OUTPUT
Write to: `./data/{category}/{slugified-title}_{YYYY-MM-DD}.md`
(Use the strict YAML frontmatter and emoji Score format from the original prompt).

### PHASE 6: GENERATE DAILY DIGEST
Create a summary digest at: `./data/digests/daily-digest-{YYYY-MM-DD}.md`
Include: 🟢 Must-Read (≥3), 🟡 Worth Knowing (0–2), 🔴 Low Relevance (<0), Feed Status Report, and Statistics.

### PHASE 7: UPDATE DEDUP INDEX
The Python core pipeline updates `./data/processed-index.json` automatically.

---

## Sources Configuration

RSS sources live in:
`./data/sources.yaml`

Update this file to add/remove feeds. The core pipeline will read it directly.
