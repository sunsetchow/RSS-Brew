# OpenClaw RSS-Brew (Native Async Architecture)

This is the OpenClaw-native branch of RSS-Brew.

- **Fetch & extract**: Python pipeline (`core_pipeline.py`) using `feedparser` + `trafilatura`.
- **Analysis**: OpenClaw SMART model performs scoring, summaries, and deep analysis.
- **Outputs**: Markdown articles + daily digest under `./data/` (or `$RSS_DATA_DIR`).

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Copy and edit your sources
cp sources.example.yaml ./data/sources.yaml

# Run the pipeline
python ./core_pipeline.py --sources ./data/sources.yaml --dedup ./data/processed-index.json --output ./data/new-articles.json
```

See `SKILL.md` for the full automation protocol and LLM analysis steps.
