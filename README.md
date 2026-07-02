# RepoPilot AI

RepoPilot AI is an AI Engineering Copilot for codebase understanding, debugging, and developer onboarding.

## Project Goal

RepoPilot AI helps developers understand unfamiliar repositories, debug errors, generate setup instructions, and create documentation using retrieval-augmented generation and multi-agent workflows.

## Planned Features

- Upload or connect a GitHub repository
- Ingest and chunk source code files
- Store code embeddings in a vector database
- Ask source-grounded questions about the codebase
- Generate architecture explanations
- Diagnose terminal errors and setup issues
- Generate README and onboarding guides
- Use multi-agent orchestration with LangGraph
- Evaluate answer quality using LLM evaluation tools
- Deploy using Docker, AWS, and GitHub Actions CI/CD

## Tech Stack

- Backend: FastAPI
- Frontend: Next.js, React, TypeScript
- AI: OpenAI API, LangGraph
- Database: PostgreSQL + pgvector
- Deployment: Docker, AWS
- CI/CD: GitHub Actions