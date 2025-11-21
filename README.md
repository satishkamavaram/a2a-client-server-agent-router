# A2A Agent Orchestration System

## Table of contents

- [Architecture Overview](#architecture-overview)
- [Components & Ports](#components--ports)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
- [Starting the Agent Servers](#starting-the-agent-servers)
- [Facade WebSocket & Frontends](#facade-websocket--frontends)
- [Agent Card Discovery](#agent-card-discovery)

A multi-agent orchestration system that intelligently routes user queries to specialized agents:

**🗄️ PostgreSQL Database Agent**: Generates SQL queries using llm and executes database operations
- top 5 customers with total number of sales with total sale amount more than 3700
- show me largest sale happened in 2025

**Jira Agent**: Jira-focused assistant powered via MCP tools
- Fetch tickets, map userId → email, and create appointments via tools

**Orchestration Agent**: Smart router that determines which specialist agent to invoke
- Intelligent query analysis and routing
- A2A protocol communication between agents
- Unified response handling

**MCP Server**: Provides tools (Jira, weather, appointment) over HTTP MCP for Jira Agent

**Facade Agent**: WebSocket bridge for UIs; proxies to Orchestration and MCP

**Frontends**: Two React UIs
- ai-chat-frontend-keycloak-auth (with Keycloak)


## Architecture Overview

```
User → Frontend (WebSocket) → Facade (8081) → Orchestration (10003) → [DB (10000) | Jira (10002)]
                                                             ↓
                                                       Formatted Response
```

**Communication Protocols**
- Agent-to-Agent (A2A) over HTTP
- WebSocket for UI ↔ Facade streaming
- MCP over HTTP for tool invocation

## Components & Ports
- PostgreSQL DB Agent: 10000
- Jira Agent: 10002
- Orchestration Agent: 10003
- Facade (WebSocket): 8081
  - WebSocket endpoint: ws://localhost:8081/ai-agent/ws/{client_id}
- MCP Server (FastMCP): 8001 (http://localhost:8001/mcp)
- Frontend (UI): 3000
---

## Prerequisites
- Python 3.10+
- PostgreSQL database (for DB agent)
- An OpenAI API key

Create a `.env` file in each agent directory with:

```
OPENAI_API_KEY=your_openai_api_key
```

---

## Setup Instructions

Each agent/facade/mcp requires its own virtual environment and dependencies. Follow these steps in order:

### Mandatory .env keys (quick reference)
- PostgreSQL DB Agent (10000):
  - OPENAI_API_KEY
  - postgres_url (e.g., postgresql://user:pass@localhost:5432/dbname)
- Jira Agent (10002):
  - OPENAI_API_KEY
  - MCP_SERVER_URL (e.g., http://localhost:8001/mcp)


### 2. PostgreSQL Database Agent Setup (Port 10000)
From the `postgres-db-agent/` folder:

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env with mandatory keys
cat > .env << 'EOF'
OPENAI_API_KEY=your_openai_api_key
# PostgreSQL connection URL (note: key name is lowercase 'postgres_url')
# Format: postgresql://USER:PASS@HOST:PORT/DBNAME
postgres_url=postgresql://admin:admin@localhost:5432/ai
EOF
```

### 3. MCP Server Setup (Port 8001)
From the repo root (FastMCP server at `mcp/mcp_server.py`):

```bash
# (Optional) Use a dedicated venv
python3 -m venv .venv-mcp
source .venv-mcp/bin/activate
pip install fastmcp
```

### 4. Jira Agent Setup (Port 10002)
From the `jira-agent/` folder:

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with OpenAI API key and MCP server URL
cat > .env << 'EOF'
OPENAI_API_KEY=your_openai_api_key
MCP_SERVER_URL=http://localhost:8001/mcp
EOF
```

### 5. Orchestration Agent Setup (Port 10003)
From the `orchestration-agent/` folder:

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << 'EOF'
OPENAI_API_KEY=your_openai_api_key

DB_AGENT_URL=http://localhost:10000
JIRA_AGENT_URL=http://localhost:10002
EOF
```


---

## Starting the Agent Servers

**⚠️ Important**: Start the servers in this exact order to ensure proper dependencies:

### 1. Start MCP Server (Port 8001)
```bash
cd mcp/
source .venv-mcp/bin/activate
python mcp_server.py
```

### 2. Start PostgreSQL Database Agent (Port 10000)
```bash
cd postgres-db-agent/
source .venv/bin/activate
python a2a_postgres_agent.py
```

### 3. Start Jira Agent (Port 10002)
```bash
cd jira-agent/
source .venv/bin/activate
python a2a_jira_server.py
```

### 4. Start Orchestration Agent (Port 10003)
```bash
cd orchestration-agent/
source .venv/bin/activate
python orchestration_agent.py
```

### 5. Start Facade (Port 8081)
The Facade hosts WebSocket endpoints and proxies to Orchestration at http://localhost:10003.

```bash
cd facade-agent/
python3 -m venv venv
source venv/bin/activate
pip install -e .   
cd src/
uvicorn ai_app.app:app --host 0.0.0.0 --port 8081
```


---


### Frontend (Keycloak auth - Install keycloak server as a pre-requisite)
From `ai-chat-frontend-keycloak-auth/`:

```bash
npm install
npm start
```

Keycloak config is in `ai-chat-frontend-keycloak-auth/src/auth/keycloak.js`:
- url: http://localhost:8080/
- realm: satishrealm
- clientId: testclient

Both UIs auto-generate a client_id(keycloak accesstoken for keycloak auth ui) for the WebSocket and provide a simple chat.



## Agent Card Discovery

Each agent exposes its capabilities through an agent card. To download agent cards:

```bash
# PostgreSQL DB Agent  
curl -H "Authorization: Bearer your_token" \
  http://localhost:10000/.well-known/agent-card.json

# Orchestration Agent (10003)
curl -H "Authorization: Bearer your_token" \
  http://localhost:10003/.well-known/agent-card.json

# Jira Agent (10002)
curl -H "Authorization: Bearer your_token" \
  http://localhost:10002/.well-known/agent-card.json
```

Or simply visit in your browser:
- http://localhost:10001/.well-known/agent-card.json
- http://localhost:10000/.well-known/agent-card.json  
- http://localhost:10003/.well-known/agent-card.json
- http://localhost:10002/.well-known/agent-card.json

---
