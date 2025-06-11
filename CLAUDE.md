# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

- **Install dependencies**: `uv sync`
- **Run the application**: `uv run python main.py`
- **Run individual modules**: `uv run python -m <module_name>`
- **Add new dependencies**: `uv add <package_name>`
- **Activate environment**: `source .venv/bin/activate` (or use `uv run` prefix)

## Architecture Overview

This is a PocketFlow-based question-answering application that uses a node-based workflow architecture:

- **Main Entry Point**: `main.py` - Creates and runs the Q&A flow
- **Flow Definition**: `flow.py` - Defines the workflow using PocketFlow nodes
- **Node Implementation**: `nodes.py` - Contains custom node classes (GetQuestionNode, AnswerNode)
- **Utilities**: `utils/call_llm.py` - OpenAI API integration for LLM calls

### Flow Architecture

The application follows a simple two-node workflow:
1. **GetQuestionNode** - Captures user input question
2. **AnswerNode** - Processes question through LLM and returns answer

Data flows through a shared dictionary that gets passed between nodes. The flow uses PocketFlow's node connection syntax (`>>`) to chain processing steps.

## Environment Requirements

- Requires `OPENAI_API_KEY` environment variable for LLM functionality
- Uses GPT-4o model by default (configurable in `utils/call_llm.py`)