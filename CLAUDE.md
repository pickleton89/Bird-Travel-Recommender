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

### API Keys Setup
1. Copy `.env.example` to `.env`: `cp .env.example .env`
2. Fill in your actual API keys in the `.env` file:
   - **OPENAI_API_KEY**: Get from https://platform.openai.com/api-keys
   - **EBIRD_API_KEY**: Get from https://ebird.org/api/keygen

### Configuration
- Uses GPT-4o model by default (configurable in `utils/call_llm.py`)
- Environment variables loaded automatically via python-dotenv
- Default settings can be configured in `.env` file

## Claude Memories

- Add to claude memory not the graphiti memory