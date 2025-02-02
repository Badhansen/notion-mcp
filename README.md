# notion-mcp

A simple Model Context Protocol (MCP) server that integrates with Notion's API to manage my personal todo list.

## Prerequisites

-   Python 3.11 or higher
-   A Notion account with API access
-   A Notion integration token
-   A Notion page where you want to manage your todo list

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

## Development

Project structure:

```markdown
notion-mcp/
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
