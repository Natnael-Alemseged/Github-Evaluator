# Automaton Auditor

Automaton Auditor is a sophisticated LangGraph-based AI system that acts as a forensic codebase evaluator. It utilizes advanced agentic workflows to dissect repositories, analyze documentation, and run multidimensional judicial scoring to generate a highly detailed and rigorous grading report.

## Architecture

The underlying system runs as a multi-stage directed graph (`src/graph.py`), employing strict **Fan-Out** and **Fan-In** patterns for distributed parallel analysis:

1. **Initialization:** Opens at `load_rubric` to parse the `rubric.json` evaluation criteria.
2. **First Fan-Out (The Detectives):** The graph splits into parallel branches to gather raw, objective `Evidence`.
   - `load_rubric` → `repo_investigator`, `doc_analyst`, and `vision_inspector`
3. **First Fan-In (The Aggregator):** The detective endpoints merge their evidence dictionaries.
   - detectives → `evidence_aggregator`
4. **Second Fan-Out (The Judges):** A conditional edge (`evidence_router`) checks for actual evidence. If found, it routes to `judges_entry`, which then forcefully expands to three distinct AI profiles.
   - `judges_entry` → `prosecutor`, `defense`, `tech_lead`
5. **Second Fan-In (The Synthesis):** The individual `JudicialOpinion` objects merge into a single node.
   - judges → `chief_justice`
6. **Finalization:** The Chief Justice outputs a report object, which passes to `report_writer` to formulate the final markdown output.

![Automaton Auditor Architecture](architecture.png)

## Core Theoretical Concepts

### 1. Dialectical Synthesis

The core of the evaluation mechanism (`src/nodes/judges.py`) is grounded in a **Dialectical Synthesis**. Instead of relying on a single LLM to provide a "fair" grade, the graph deploys three separate judge personas simultaneously on the same evidence:

- **The Prosecutor** actively seeks flaws, gaps, security vulnerabilities, and lack of rigor.
- **The Defense** highlights context, architectural constraints, and engineering strengths.
- **The Tech Lead** focuses on the objective viability of the tool as a "production-grade" system.

By pitting these opposing contexts against each other, the LLM avoids generic middle-of-the-road answers. The synthetic compromise is deterministic (via mathematical averaging in `chief_justice`), providing a more robust final score.

### 2. Metacognition & Integrity Correctness

The `Chief Justice` and `evidence_aggregator` nodes implement a layer of **Metacognition**—the system actively evaluates its own thought process prior to writing the report.

- **Dissent Tracking:** If the gap between the Prosecutor and Tech Lead exceeds a set variance margin, the AI logs this as a "Major Variance" and triggers an internal tie-breaker mechanic prioritizing the Tech Lead's practical view.
- **Hallucination Policing:** The system actively lists all literal file names in the target repo in `verified_paths`. If an AI judge or detective accidentally cites a file that doesn't exist (e.g. referencing a "setup.py" when only "pyproject.toml" exists), the system logs it as a "Hallucinated Path".
- **Global Security Veto:** If the Prosecutor flags a `score=1` on a security criteria, the system overrides the averaged consensus and immediately caps the entire repository score down to 2.0.

### 3. Forensic Depth

The system employs real programmatic extraction through `RepoInvestigator`, parsing deep into Python abstract syntax trees (`ast.walk`), strictly scanning Git history (`git log --oneline --reverse`), and ingesting technical requirements via FAISS vector DB queries, thereby grounding the LLM in undeniable, irrefutable data points.
