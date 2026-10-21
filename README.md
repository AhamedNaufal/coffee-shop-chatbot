# MCP Coffee Shop Chatbot

A chatbot for a coffee shop, built from two services that talk to each other over the
[Model Context Protocol (MCP)](https://modelcontextprotocol.io):

| Service | Folder | What it does | Default port |
|---|---|---|---|
| **MCP Client** | `mcp-client/` | FastAPI REST API. Receives the customer's message, redacts personal data, runs an AI agent (AWS Bedrock + LangGraph) and returns the reply. Remembers each conversation in PostgreSQL. | `8080` |
| **MCP Server** | `mcp-server/` | FastMCP server. Exposes the coffee shop's **tools**, **resources** and **prompts** and owns the shop database (customers, items, orders). | `8000` |

---

## How it works

```
 Customer / Postman / Frontend
              │  POST /api/v1/chatbot
              ▼
   ┌─────────────────────────┐        ┌───────────────────┐
   │       MCP Client        │───────▶│   AWS Bedrock     │  (LLM)
   │  FastAPI + LangGraph    │        └───────────────────┘
   │  • PII redaction        │
   │  • Agent + memory       │        ┌───────────────────┐
   │                         │───────▶│ PostgreSQL        │  (conversation memory)
   └───────────┬─────────────┘        └───────────────────┘
               │ MCP over HTTP (streamable-http)
               ▼
   ┌─────────────────────────┐        ┌───────────────────┐
   │       MCP Server        │───────▶│ PostgreSQL        │  (customers, items, orders)
   │  FastMCP + SQLAlchemy   │        └───────────────────┘
   └─────────────────────────┘
```

1. The client receives `customer_uuid` and `user_query`.
2. Emails, credit card numbers, IP addresses and URLs in the message are **redacted** before they reach the model.
3. The client connects to the MCP server, loads its tools, prompts and resources, and runs the agent.
4. The agent calls tools (for example, checking stock or placing an order) and builds a reply.
5. The conversation is saved in PostgreSQL under `customer_uuid`, so the next message continues the same conversation.

### What the MCP server exposes

| Type | Name | Purpose |
|---|---|---|
| Tool | `check_order_status(order_id)` | Look up the status of an order |
| Tool | `check_inventory(item_name)` | Check stock for a menu item |
| Tool | `place_order(customer_id, items)` | Place an order, for example `[{"item_name": "Coffee", "quantity": 2}]` |
| Resource | `menu://items` | The full menu |
| Resource | `shop://location` | Shop location and details |
| Prompt | `diet_planning` | Guides diet and health related questions |
| Prompt | `explain_menu` | Guides menu questions |
| Prompt | `normal_prompt` | General tool-selection guidance |

On startup the server creates its tables and inserts sample customers and menu items.

---

## Tech stack

- Python 3.14
- [uv](https://docs.astral.sh/uv/) for dependency management
- FastAPI and Uvicorn (client), FastMCP (server)
- LangChain, LangGraph and `langchain-mcp-adapters`
- AWS Bedrock (LLM) through `boto3` and `langchain-aws`
- PostgreSQL with SQLAlchemy (server) and the LangGraph Postgres checkpointer (client)

---

## Project structure

```
dev/
├── .gitignore
├── README.md
├── mcp-client/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── .python-version
│   └── src/
│       ├── app.py                 # FastAPI entry point
│       ├── setting.py             # Environment configuration
│       ├── agents/                # Agent, MCP client wiring, system prompt
│       ├── routes/                # API routes
│       ├── services/              # Business logic and PII redaction
│       ├── models/                # Request/response models, custom exception
│       └── utils/errors/          # Error codes, HTTP status codes, error logger
└── mcp-server/
    ├── pyproject.toml
    ├── uv.lock
    ├── .python-version
    └── src/
        ├── app.py                 # FastMCP entry point
        ├── setting.py             # Environment configuration
        ├── routes/                # MCP router
        ├── tools/                 # MCP tools
        ├── resources/             # MCP resources (menu, location)
        ├── prompts/               # MCP prompts
        ├── repositories/          # Database access and table definitions
        └── migrations/            # Table creation and sample data
```

---

## Prerequisites

1. **Python 3.14** (both services require it).
2. **uv**: install from <https://docs.astral.sh/uv/getting-started/installation/>.
3. **PostgreSQL** running locally or remotely, with an **empty database already created** (the services create tables but not the database itself):
   ```sql
   CREATE DATABASE mcp_chatbot;
   ```
4. **AWS account** with access to a Bedrock model in your chosen region, and an access key for it.

---

## Setup

Run these steps once per service.

### 1. Clone the repository

```bash
git clone https://github.com/AhamedNaufal/coffee-shop-chatbot.git

cd coffee-shop-chatbot

```

### 2. Install dependencies

```bash
cd mcp-server
uv sync
cd ../mcp-client
uv sync
```

Each service gets its own `.venv` folder.

### 3. Create the `.env` files

Each service needs its own `.env` file inside its **service folder** (next to `pyproject.toml`, not inside `src/`). `.env` files are git-ignored, so your secrets are never committed.

**`mcp-server/.env`**

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mcp_chatbot
DB_USERNAME=postgres
DB_PASSWORD=your_database_password
```

**`mcp-client/.env`**

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mcp_chatbot
DB_USERNAME=postgres
DB_PASSWORD=your_database_password

REGION=your_aws_region
MODEL_ID=your_bedrock_model_id
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key

MCP_SERVER_URL=http://localhost:8000/mcp
# ERROR_LOG_URL=http://localhost:9000/api/v1/error
```

---

## Environment variables

### MCP Server

| Variable | Required | Default | Description |
|---|---|---|---|
| `DB_PASSWORD` | Yes | none | PostgreSQL password |
| `DB_HOST` | No | `localhost` | PostgreSQL host |
| `DB_PORT` | No | `5432` | PostgreSQL port |
| `DB_NAME` | No | `mcp_chatbot` | Database name |
| `DB_USERNAME` | No | `postgres` | Database user |

### MCP Client

| Variable | Required | Default | Description |
|---|---|---|---|
| `DB_PASSWORD` | Yes | none | PostgreSQL password. The app stops at startup if it is missing. |
| `DB_HOST` | No | `localhost` | PostgreSQL host |
| `DB_PORT` | No | `5432` | PostgreSQL port |
| `DB_NAME` | No | `mcp_chatbot` | Database name (stores conversation memory) |
| `DB_USERNAME` | No | `postgres` | Database user |
| `REGION` | Yes | none | AWS region for Bedrock, for example `us-east-1` |
| `MODEL_ID` | Yes | none | Bedrock model ID your account has access to |
| `AWS_ACCESS_KEY_ID` | Yes | none | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | Yes | none | AWS secret key |
| `MCP_SERVER_URL` | No | `http://localhost:8000/mcp` | Address of the MCP server |
| `ERROR_LOG_URL` | No | empty (disabled) | Your own error-logging endpoint (see below) |
| `HOST` | No | `0.0.0.0` | Address the client API listens on |
| `PORT` | No | `8080` | Port the client API listens on |

> **Model note:** the client is configured with `provider="amazon"` and Titan-style
> parameters (`maxTokenCount`), so use a compatible Amazon model ID that is enabled for your
> account in the chosen region.

---

## Running the application

**Always start the server first**, because the client connects to it on every request.

### 1. Start the MCP server

```bash
cd mcp-server/src
uv run python app.py
```

On startup it creates the tables and inserts sample data. The MCP endpoint is
`http://localhost:8000/mcp`.

### 2. Start the MCP client

Open a second terminal:

```bash
cd mcp-client/src
uv run python app.py
```

The API is now available at `http://localhost:8080`, with interactive docs at
`http://localhost:8080/docs`.

> Run both commands from inside each `src/` folder. The imports are written relative to it.

---

## Using the API

### `POST /api/v1/chatbot`

| Field | Type | Description |
|---|---|---|
| `customer_uuid` | string | Identifies the conversation. Reuse the same value to continue a conversation. |
| `user_query` | string | The customer's message |

**Example request**

```bash
curl -X POST http://localhost:8080/api/v1/chatbot \
  -H "Content-Type: application/json" \
  -d '{"customer_uuid": "customer-1", "user_query": "Do you have cappuccino in stock?"}'
```

**Example response**

```json
{
  "data": {
    "user_query": "Do you have cappuccino in stock?",
    "response": "Yes, cappuccino is available. Would you like to order one?"
  },
  "errors": [],
  "status_code": 200,
  "request_id": "3f9c2c1e-8a4b-4d57-9d0e-5b6f6d2c1a10",
  "message": "Success"
}
```

**Error response:** failures return the same structure, with `errors` filled in and an HTTP
status such as `422` (invalid request body) or `500` (internal error).

---

## Optional: error logging

The client always prints errors to the console. If you set `ERROR_LOG_URL`, it also sends each
error to your own logging service with a `POST` request (3-second timeout):

```json
{
  "file_name": "agent.py",
  "function_name": "chatbot_agent",
  "error_message": "..."
}
```

Build any endpoint that accepts this JSON, run it, and put its address in `ERROR_LOG_URL`.
If the variable is not set, nothing is sent.

---

## Security notes

- Never commit `.env` files. They are listed in `.gitignore`.
- Use your own database password and AWS credentials; no defaults are provided for them.
- User messages are redacted for emails, credit card numbers, IP addresses and URLs before
  reaching the model, but this is not a complete privacy guarantee.
- CORS is currently open to all origins (`allow_origins=["*"]`) and the client runs with auto-reload.
  Restrict both before deploying to production.

---

## Troubleshooting

| Problem | Likely cause and fix |
|---|---|
| `Missing required environment variable: DB_PASSWORD` | The `.env` file is missing or in the wrong folder. It must sit next to `pyproject.toml`. |
| `database "mcp_chatbot" does not exist` | Create the database first (see Prerequisites). |
| Client returns a 500 error mentioning a connection failure | The MCP server is not running, or `MCP_SERVER_URL` is wrong. Start the server first. |
| `ModuleNotFoundError` on startup | You started the app from the wrong folder. Run it from inside `src/`. |
| Bedrock access denied or invalid model/region | Check `REGION`, `MODEL_ID`, the AWS keys, and that model access is enabled in your AWS account. |
| `uv sync` fails on Python version | Install Python 3.14 (`uv python install 3.14`). |
| Port already in use | Another process uses 8000 or 8080. Stop it, or change the client `PORT`. |

---

## Contributing

1. Create a branch from `main`.
2. Keep secrets out of commits.
3. Run both services and send a test request before opening a pull request.
