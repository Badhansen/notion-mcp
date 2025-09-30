# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Model Context Protocol (MCP) server that integrates with Notion's API to manage todo lists. The server provides three main functions: adding todos, viewing all todos, and marking todos as complete.

## Development Environment

-   **Python Version**: 3.11 or higher (specified in `.python-version`)
-   **Package Manager**: `uv` (preferred)
-   **Virtual Environment**: `.venv` directory

## Setup Commands

```bash
# Set up virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .

# Run the MCP server
uv --directory src run server.py
```

## Configuration

The project requires environment variables defined in `.env`:

-   `NOTION_TOKEN`: Notion API integration token
-   `PAGE_ID`: Target Notion page ID for todo management
-   `NOTION_VERSION`: API version (typically "2022-06-28")
-   `NOTION_BASE_URL`: Base URL for Notion API

## Architecture

### Core Components

-   **`src/server.py`**: Single main file containing the entire MCP server implementation
-   **Server Class**: Uses the `mcp.server.Server` framework
-   **Async Functions**: All Notion API interactions are asynchronous using `httpx.AsyncClient`

### MCP Tools

The server implements three tools:

1. `add_todo` - Creates new todo items on the Notion page
2. `show_all_todos` - Fetches and displays all todos with their completion status
3. `complete_todo` - Marks a specific todo as completed using its task_id

### Key Functions

-   `fetch_todos_on_page()`: Handles pagination to retrieve all todo blocks from a Notion page
-   `create_todo_on_page()`: Adds new todo blocks using PATCH to `/blocks/{PAGE_ID}/children`
-   `complete_todo_on_page()`: Updates todo completion status using PATCH to `/blocks/{task_id}`

### Error Handling

The codebase includes comprehensive error handling for:

-   Missing environment variables
-   Notion API HTTP errors
-   Invalid function arguments
-   Missing todo items

## Integration with Claude Desktop

Configure in `claude_desktop_config.json`:

```json
{
    "mcpServers": {
        "notion-mcp": {
            "command": "uv",
            "args": [
                "--directory",
                "/path/to/notion-mcp/src",
                "run",
                "server.py"
            ]
        }
    }
}
```

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Model Context Protocol (MCP) server that integrates with Notion's API to manage todo lists. The server provides three main functions: adding todos, viewing all todos, and marking todos as complete.

## Development Environment

-   **Python Version**: 3.11 or higher (specified in `.python-version`)
-   **Package Manager**: `uv` (preferred)
-   **Virtual Environment**: `.venv` directory

## Setup Commands

```bash
# Set up virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .

# Run the MCP server
uv --directory src run server.py

# Test with MCP Inspector
npx @modelcontextprotocol/inspector \
  uv \
  --directory /Users/badhan/Projects/Python/notion-mcp/src \
  run \
  server.py
```

## Configuration

The project requires environment variables defined in `.env`:

-   `NOTION_TOKEN`: Notion API integration token
-   `PAGE_ID`: Target Notion page ID for todo management
-   `NOTION_VERSION`: API version (typically "2022-06-28")
-   `NOTION_BASE_URL`: Base URL for Notion API

## Architecture

### Core Components

-   **`src/server.py`**: Single main file containing the entire MCP server implementation
-   **Server Class**: Uses the `mcp.server.Server` framework
-   **Async Functions**: All Notion API interactions are asynchronous using `httpx.AsyncClient`

### MCP Tools

The server implements three tools:

1. `add_todo` - Creates new todo items on the Notion page
2. `show_all_todos` - Fetches and displays all todos with their completion status
3. `complete_todo` - Marks a specific todo as completed using its task_id

### Key Functions

-   `fetch_todos_on_page()`: Handles pagination to retrieve all todo blocks from a Notion page
-   `create_todo_on_page()`: Adds new todo blocks using PATCH to `/blocks/{PAGE_ID}/children`
-   `complete_todo_on_page()`: Updates todo completion status using PATCH to `/blocks/{task_id}`

### Error Handling

The codebase includes comprehensive error handling for:

-   Missing environment variables
-   Notion API HTTP errors
-   Invalid function arguments
-   Missing todo items

## Integration with Claude Desktop

Configure in `claude_desktop_config.json`:

```json
{
    "mcpServers": {
        "notion-mcp": {
            "command": "uv",
            "args": [
                "--directory",
                "/path/to/notion-mcp/src",
                "run",
                "server.py"
            ]
        }
    }
}
```

## Deployment

The project supports deployment via Smithery with configuration in `smithery.yaml`. The Smithery configuration handles environment variable mapping and provides a schema for required configuration options.
