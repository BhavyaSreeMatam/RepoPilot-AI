# RepoPilot AI

RepoPilot AI is a full-stack AI engineering copilot for understanding, onboarding into, debugging, and reviewing unfamiliar codebases. Users authenticate, upload a repository ZIP, index the codebase, and interact with specialized AI agents that return source-grounded answers.

## What RepoPilot Does

- Authenticated sign-in/sign-up with Amazon Cognito
- Per-user repository isolation with Amazon DynamoDB ownership metadata
- Repository ZIP upload, safe extraction, scanning, deletion, and persistent storage
- Batched OpenAI embeddings for faster indexing
- ChromaDB vector search for repository-aware retrieval
- LangGraph orchestration with router, retriever, specialized-agent, and verifier stages
- MCP server with specialized architecture, bug, security, documentation, and general agents
- Onboarding summaries, architecture Q&A, debugging assistance, and security review
- Source file references and line ranges in answers
- Dockerized frontend and backend
- AWS EC2 + ECR deployment
- Automatic deployment from GitHub `master` through AWS CodeBuild and SSM
- GitHub Actions CI for frontend and backend checks

## Final Architecture

```mermaid
flowchart LR
    U[User Browser] -->|Sign in / Sign up| COG[Amazon Cognito]
    U -->|Bearer token + requests| FE[React / Vite Frontend\nNginx]

    FE -->|/api| API[FastAPI Backend]
    API --> AUTH[Cognito JWT Verification]
    AUTH --> OWN[DynamoDB Repository Ownership]

    API --> FILES[Uploaded ZIP + Extracted Repositories]
    API --> IDX[Code Scanner + Chunker]
    IDX --> EMB[OpenAI Embeddings\nBatched]
    EMB --> CHROMA[ChromaDB Vector Store]

    API --> GRAPH[LangGraph Orchestrator]
    GRAPH --> ROUTER[Router]
    ROUTER --> RET[Retriever]
    RET --> CHROMA
    RET --> MCP[MCP Specialized-Agent Server]
    MCP --> ARCH[Architecture Agent]
    MCP --> BUG[Bug Agent]
    MCP --> SEC[Security Agent]
    MCP --> DOC[Docs Agent]
    MCP --> GEN[General Agent]
    MCP --> OAI[OpenAI Chat Models]
    GRAPH --> VERIFY[Verifier]
    VERIFY --> OAI
    VERIFY --> API
```

## AWS Deployment Architecture

```mermaid
flowchart TB
    GH[GitHub Repository\nmaster branch] --> CI[GitHub Actions CI\nFrontend lint/build\nBackend compile/smoke]
    GH -->|Push webhook| CB[AWS CodeBuild\nRepoPilot-Deploy]
    CB -->|Build + push| ECRB[Amazon ECR\nrepopilot-backend]
    CB -->|Build + push| ECRF[Amazon ECR\nrepopilot-frontend]
    CB -->|AWS Systems Manager| EC2[Amazon EC2]
    EC2 -->|Pull latest images| ECRB
    EC2 -->|Pull latest images| ECRF
    EC2 --> NGINX[Nginx Frontend\nPort 80]
    NGINX --> FASTAPI[FastAPI Backend\nDocker network]
    FASTAPI --> DDB[DynamoDB\nRepoPilotRepositories]
    FASTAPI --> COG[Amazon Cognito]
    FASTAPI --> OPENAI[OpenAI API]
```

## Repository Structure

```text
RepoPilot-AI/
├── .github/
│   └── workflows/
│       └── ci.yml
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   ├── api/
│   │   ├── core/
│   │   ├── mcp_server/
│   │   ├── schemas/
│   │   └── services/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   ├── Dockerfile
│   └── package.json
├── buildspec.deploy.yml
├── docker-compose.yml
└── README.md
```

## Local Prerequisites

- Python 3.14
- Node.js 22+
- npm
- Docker Desktop (optional for local container testing)
- AWS CLI with the `repopilot` profile if using the deployed DynamoDB/Cognito resources locally
- OpenAI API key

## Environment Variables

Create `backend/.env` from `.env.example`. Do not commit `.env`.

```env
OPENAI_API_KEY=your_openai_api_key
DATABASE_URL=postgresql://username:password@localhost:5432/repopilot
ENVIRONMENT=development
AWS_REGION=us-east-2
COGNITO_USER_POOL_ID=your_cognito_user_pool_id
COGNITO_APP_CLIENT_ID=your_cognito_app_client_id
REPOSITORY_TABLE_NAME=RepoPilotRepositories
```

For the frontend, create `frontend/.env.local`:

```env
VITE_AWS_REGION=us-east-2
VITE_COGNITO_USER_POOL_ID=your_cognito_user_pool_id
VITE_COGNITO_USER_POOL_CLIENT_ID=your_cognito_app_client_id
```

## Run Locally

### Backend

```powershell
cd D:\Projects\RepoPilot-AI\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install "botocore[crt]"

$env:AWS_PROFILE = "repopilot"
$env:AWS_REGION = "us-east-2"

uvicorn app.main:app --reload --reload-dir app
```

Backend health:

```powershell
curl.exe http://127.0.0.1:8000/health
```

### Frontend

```powershell
cd D:\Projects\RepoPilot-AI\frontend
npm ci
npm run dev
```

Open `http://localhost:5173`.

> Use `--reload-dir app` for the backend. Plain `--reload` can watch uploaded/extracted repositories and restart Uvicorn during uploads.

## Main API Routes

| Route | Purpose |
|---|---|
| `GET /health` | Public backend health check |
| `POST /repos/upload` | Upload and extract a repository ZIP |
| `GET /repos` | List repositories owned by the signed-in user |
| `DELETE /repos/{repo_id}` | Delete owned repository data and vector index |
| `GET /repos/{repo_id}/scan` | Scan repository structure/languages |
| `GET /repos/{repo_id}/chunks` | Inspect generated chunks |
| `POST /repos/{repo_id}/index` | Build repository embeddings/vector index |
| `GET /repos/{repo_id}/search` | Search indexed repository chunks |
| `POST /agent/ask` | Ask architecture/general/security questions |
| `POST /agent/summarize` | Generate onboarding summary |
| `POST /agent/debug` | Debug a repository-specific issue |

All repository and agent routes except `/health` require a valid Cognito access token and repository ownership.

## Application Flow

1. User authenticates with Cognito.
2. Frontend obtains a Cognito access token.
3. Every protected API request sends `Authorization: Bearer <access token>`.
4. Backend verifies the JWT issuer, signature, expiry, token type, app client, and user `sub`.
5. User uploads a ZIP; FastAPI safely extracts and scans it.
6. Repository ownership metadata is stored in DynamoDB using `owner_sub + repo_id`.
7. User indexes the repository; code is chunked and embeddings are generated in batches.
8. Chunks and embeddings are persisted in ChromaDB.
9. Agent requests verify ownership, retrieve relevant chunks, route through LangGraph/MCP agents, and run verifier grounding.
10. The frontend displays the answer, sources, execution steps, and verification information.
11. Deleting a repository removes its uploaded/extracted files, vector index, and DynamoDB metadata.

## CI/CD

### GitHub Actions

`.github/workflows/ci.yml` runs on pushes and pull requests and performs:

- Frontend `npm ci`, lint, and production build
- Backend dependency installation, compile check, and import smoke test

### AWS CodeBuild Deployment

`buildspec.deploy.yml` is used by the `RepoPilot-Deploy` CodeBuild project. A push to `master` triggers CodeBuild through a GitHub webhook.

CodeBuild:

1. Logs in to ECR.
2. Creates a short commit image tag.
3. Builds backend and frontend Docker images.
4. Pushes versioned and `latest` tags to ECR.
5. Sends an SSM command to the RepoPilot EC2 instance.
6. EC2 pulls the latest images and recreates the containers.
7. Deployment waits for backend health and verifies frontend/backend through Nginx.

Normal deployment workflow:

```powershell
git add .
git commit -m "Describe the change"
git push origin master
```

## AWS Resource Inventory

| Service | RepoPilot Resource |
|---|---|
| EC2 | RepoPilot application host |
| ECR | `repopilot-backend` |
| ECR | `repopilot-frontend` |
| IAM | `RepoPilotEC2Role` |
| IAM | `RepoPilotCodeBuildRole` |
| Cognito | `RepoPilotUsers` user pool |
| Cognito | `RepoPilotWebClient` app client |
| DynamoDB | `RepoPilotRepositories` |
| SSM Parameter Store | `/repopilot/openai-api-key` |
| CodeBuild | `RepoPilot-Deploy` |
| CodeConnections | `RepoPilotGitHubConnection` |
| GitHub Actions | `.github/workflows/ci.yml` |
| CodeBuild buildspec | `buildspec.deploy.yml` |

## Security Design

- OpenAI API key is not committed to Git.
- Production OpenAI key is stored in AWS SSM Parameter Store.
- EC2 uses an IAM instance role instead of static AWS credentials.
- CodeBuild uses its own least-privilege IAM role.
- GitHub is connected to AWS through a GitHub App/CodeConnections rather than long-lived AWS keys.
- Repository access is scoped by Cognito `sub` and DynamoDB ownership metadata.
- Unauthorized repository lookups return `404` to avoid leaking repository existence.
- ZIP extraction validates target paths to reduce path traversal risk.
- Security scanning checks patterns such as unsafe deserialization, secrets, command execution, insecure configuration, cryptographic weaknesses, Docker/CI/CD risks, and unsafe file handling.

## Important Current Limitation

The portfolio deployment currently uses the EC2 public IPv4 address over **HTTP**. Authentication works, but the demo should not be treated as production-grade until HTTPS is added. Avoid uploading sensitive/private repositories to the public demo.

## Troubleshooting

### Local DynamoDB error with AWS login credentials

If boto3 reports that the login credential provider requires an additional dependency:

```powershell
pip install "botocore[crt]"
```

### Upload causes Uvicorn to restart

Start the backend with:

```powershell
uvicorn app.main:app --reload --reload-dir app
```

### Indexing is slow or times out

RepoPilot batches embedding requests instead of making one OpenAI call per chunk. The current implementation uses batches of 32.

### Indexed badge does not update

The frontend updates repository state immediately after a successful indexing request. Reloading should not be required.

### Agent endpoints return no visible answer

Check the browser Network response and backend logs. A `200 OK` from `/agent/ask` plus a valid JSON answer usually indicates a frontend rendering/state problem rather than an OpenAI/MCP failure.

## Portfolio Summary

RepoPilot AI demonstrates full-stack and AI engineering across RAG, vector retrieval, LangGraph orchestration, MCP agents, deterministic security scanning, authentication and authorization, AWS deployment, Docker, persistent storage, and automated CI/CD.
