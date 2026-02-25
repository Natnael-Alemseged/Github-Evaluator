# Automaton Auditor

FDE Challenge Week 2 - The Automaton Auditor. This is a production-grade multi-agent system designed to forensically audit codebases.

## Setup Instructions

1. Install dependencies using [uv](https://docs.astral.sh/uv/):

   ```bash
   uv sync
   ```

2. Set up environment variables:

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your API keys.

3. Activate the environment:

   ```bash
   source .venv/bin/activate
   ```

4. Run the auditor:
   ```bash
   uv run python -m src.graph
   ```
