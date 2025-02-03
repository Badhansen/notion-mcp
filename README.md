# notion-mcp

A simple Model Context Protocol (MCP) server that integrates with Notion's API to manage my personal todo list.

## Demo

<div align="center">
  <video src="https://github.com/Badhansen/notion-mcp/assets/videos/notion-mcp.mp4" width="600" />
</div>

![Notion MCP Query 1](docs/assets/images/query1.png)

![Notion MCP Query 1](docs/assets/images/query1.png)

![Notion MCP Query 1](docs/assets/images/query1.png)

## Prerequisites

-   Python 3.11 or higher
-   A Notion account with API access
-   A Notion integration token
-   A Notion page where you want to manage your todo list
-   Claude Desktop clint

## Setup

1. Clone the repository:

```sh
git clone https://github.com/Badhansen/notion-mcp.git
cd notion-mcp
```

2. Set up Python environment:

```sh
uv venv
source .venv/bin/activate
uv pip install -e .
```

3. Create a Notion integration:
    - Go to https://www.notion.so/my-integrations
    - Create new integration
    - Copy the API key
4. Share your database/page with the integration:
    - Open your notion workspace with a database/table present or a page.
    - Click "..." menu → "Add connections"
    - Select your integration (Search by name)

## Configuration

1. Create `.env` file:

```sh
cp .env.example .env
```

2. Configure Notion credentials in `.env`:

```markdown
NOTION_TOKEN=<your-notion-api-token>
PAGE_ID=<your-notion-page-id>
NOTION_VERSION="2022-06-28"
NOTION_BASE_URL="https://api.notion.com/v1"
```

3. To use it with Claude Desktop as intended you need to adjust your `claude_desktop_config.json` file.
   Go to `Claude Desktop -> Settings -> Developer -> Edit Config`. Now add the `Notion` server configuration.

```json
{
    "mcpServers": {
        "notion-mcp": {
            "command": "uv",
            "args": [
                "--directory",
                "/Users/username/Projects/Python/notion-mcp/src" /* Path to your project */,
                "run",
                "server.py"
            ]
        }
    }
}
```

## Development

Project structure:

```markdown
notion-mcp/
├── docs/
├── src/
│ └── server.py
├── .env
├── .python-version
├── README.md
├── pyproject.toml
└── uv.lock
```

## Contributing

1. Fork the repository
2. Create feature branch
3. Submit pull request

## License

MIT License. See LICENSE file for details.
