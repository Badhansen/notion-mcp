from mcp.types import Tool, TextContent, EmbeddedResource
from mcp.server import Server
from typing import Any, Sequence
from dotenv import load_dotenv
from pathlib import Path
import logging
import httpx
import os

# Find and load .env file from project root
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / '.env'

if not env_path.exists():
    raise FileNotFoundError(f"No .env file found at {env_path}")

load_dotenv(env_path)

# Setup logging configuration
logging.basicConfig(level=logging.INFO)


NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABSE_ID = os.getenv("DATABSE_ID")
PAGE_ID = os.getenv("PAGE_ID")

NOTION_VERSION = os.getenv("NOTION_VERSION")
NOTION_BASE_URL = os.getenv("NOTION_BASE_URL")


# Notion API headers
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION
}


# Create a named server
server = Server("notion-mcp")

async def fetch_todos_on_page(page_id: str) -> list:
    """
    Fetch all to-do items from a Notion page.
    :param page_id: The ID of the Notion page (UUID format).
    :return: A list of to-do items with text and their completion status.
    """
    async with httpx.AsyncClient() as client:
        todos = []
        has_more = True
        next_cursor = None

        while has_more:
            # Fetch child blocks from the page
            response = await client.get(
                f"{NOTION_BASE_URL}/blocks/{page_id}/children",
                headers=headers,
                params={"start_cursor": next_cursor} if next_cursor else None,
            )
            response.raise_for_status()
            data = response.json()

            # Extract to-do items
            for block in data.get("results", []):
                if block["type"] == "to_do":
                    todo_text = "".join(
                        [text["plain_text"] for text in block["to_do"]["rich_text"]]
                    )
                    is_checked = block["to_do"]["checked"]
                    todos.append({"text": todo_text, "checked": is_checked, "task_id": block["id"]})

            # Handle pagination
            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor")

        return todos

async def fetch_page_content(page_id: str) -> dict:
    """
    Fetch all content from a Notion page including blocks and metadata.
    :param page_id: The ID of the Notion page (UUID format).
    :return: Dictionary containing page metadata and content blocks.
    """
    async with httpx.AsyncClient() as client:
        # Get page metadata
        page_response = await client.get(
            f"{NOTION_BASE_URL}/pages/{page_id}",
            headers=headers
        )
        page_response.raise_for_status()
        page_data = page_response.json()

        # Get page content blocks
        blocks = []
        has_more = True
        next_cursor = None

        while has_more:
            response = await client.get(
                f"{NOTION_BASE_URL}/blocks/{page_id}/children",
                headers=headers,
                params={"start_cursor": next_cursor} if next_cursor else None,
            )
            response.raise_for_status()
            data = response.json()

            for block in data.get("results", []):
                blocks.append(block)

            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor")

        return {
            "page_metadata": page_data,
            "blocks": blocks
        }

def extract_text_from_blocks(blocks: list) -> str:
    """
    Extract plain text content from Notion blocks.
    :param blocks: List of Notion block objects.
    :return: Concatenated text content.
    """
    text_content = []

    for block in blocks:
        block_type = block.get("type")

        if block_type == "paragraph":
            text = "".join([text["plain_text"] for text in block["paragraph"]["rich_text"]])
            if text.strip():
                text_content.append(text)
        elif block_type == "heading_1":
            text = "".join([text["plain_text"] for text in block["heading_1"]["rich_text"]])
            if text.strip():
                text_content.append(f"# {text}")
        elif block_type == "heading_2":
            text = "".join([text["plain_text"] for text in block["heading_2"]["rich_text"]])
            if text.strip():
                text_content.append(f"## {text}")
        elif block_type == "heading_3":
            text = "".join([text["plain_text"] for text in block["heading_3"]["rich_text"]])
            if text.strip():
                text_content.append(f"### {text}")
        elif block_type == "bulleted_list_item":
            text = "".join([text["plain_text"] for text in block["bulleted_list_item"]["rich_text"]])
            if text.strip():
                text_content.append(f"• {text}")
        elif block_type == "numbered_list_item":
            text = "".join([text["plain_text"] for text in block["numbered_list_item"]["rich_text"]])
            if text.strip():
                text_content.append(f"1. {text}")
        elif block_type == "to_do":
            text = "".join([text["plain_text"] for text in block["to_do"]["rich_text"]])
            checked = "[x]" if block["to_do"]["checked"] else "[ ]"
            if text.strip():
                text_content.append(f"{checked} {text}")
        elif block_type == "quote":
            text = "".join([text["plain_text"] for text in block["quote"]["rich_text"]])
            if text.strip():
                text_content.append(f"> {text}")
        elif block_type == "code":
            text = "".join([text["plain_text"] for text in block["code"]["rich_text"]])
            if text.strip():
                text_content.append(f"```\n{text}\n```")

    return "\n\n".join(text_content)
    
async def create_todo_on_page(task: str) -> dict:
    """
    Add a to-do item to an existing Notion page (using the PAGE_ID from .env).
    Args:
        task (str): The text of the to-do item.
    Returns:
        dict: The response from the Notion API.
    Raises:
        ValueError: If PAGE_ID is not set in the .env file.
        httpx.HTTPStatusError: If the request to the Notion API fails.
    """
    if not PAGE_ID:
        raise ValueError("PAGE_ID is not set in the .env file.")
    
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{NOTION_BASE_URL}/blocks/{PAGE_ID}/children",
            headers=headers,
            json={
                "children": [
                    {
                        "object": "block",
                        "type": "to_do",
                        "to_do": {
                            "rich_text": [
                                {"type": "text", "text": {"content": task}}
                            ],
                            "checked": False
                        }
                    }
                ]
            }
        )
        response.raise_for_status()
        return response.json()
    
async def complete_todo_on_page(task_id: str) -> None:
    """
    Mark a to-do item as complete in a Notion Page.
    Args:
        task_id (str): The task_id of the to-do item to be marked as complete.
    Raises:
        ValueError: If there is an error completing the to-do item.
    Returns:
        None
    """
    todos = await fetch_todos_on_page(PAGE_ID)
    
    if not any(todo.get("task_id") == task_id for todo in todos):
        raise ValueError(f"No to-do item found with title: {task_id}")

    # The payload to update the block (to change the 'checked' status)
    payload = {
        "to_do": {
            "checked": True
        }
    }
     
    try:
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{NOTION_BASE_URL}/blocks/{task_id}",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logging.info("No to-do found in the page.")
        raise ValueError(f"Error completing todo: {str(e)}")

async def create_subpage(parent_page_id: str, title: str, content_blocks: list = None) -> dict:
    """
    Create a new subpage under a parent page.
    :param parent_page_id: The ID of the parent page.
    :param title: The title of the new subpage.
    :param content_blocks: Optional list of content blocks to add to the page.
    :return: The created page response.
    """
    if content_blocks is None:
        content_blocks = []

    async with httpx.AsyncClient() as client:
        # Create the page
        page_data = {
            "parent": {"page_id": parent_page_id},
            "properties": {
                "title": {
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": title}
                        }
                    ]
                }
            },
            "children": content_blocks
        }

        response = await client.post(
            f"{NOTION_BASE_URL}/pages",
            headers=headers,
            json=page_data
        )
        response.raise_for_status()
        return response.json()

async def add_content_to_page(page_id: str, content_blocks: list) -> dict:
    """
    Add content blocks to an existing page.
    :param page_id: The ID of the page to add content to.
    :param content_blocks: List of content blocks to add.
    :return: The API response.
    """
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{NOTION_BASE_URL}/blocks/{page_id}/children",
            headers=headers,
            json={"children": content_blocks}
        )
        response.raise_for_status()
        return response.json()

def create_claude_chat_summary_blocks(conversation_summary: str, key_points: list, examples: list = None) -> list:
    """
    Create Notion blocks for a Claude chat summary.
    :param conversation_summary: Brief summary of the conversation.
    :param key_points: List of key points from the conversation.
    :param examples: Optional list of examples discussed.
    :return: List of Notion block objects.
    """
    blocks = []

    # Add heading
    blocks.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "Claude Chat Summary"}}]
        }
    })

    # Add summary
    blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": conversation_summary}}]
        }
    })

    # Add key points
    if key_points:
        blocks.append({
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"type": "text", "text": {"content": "Key Points"}}]
            }
        })

        for point in key_points:
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": point}}]
                }
            })

    # Add examples if provided
    if examples:
        blocks.append({
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"type": "text", "text": {"content": "Examples"}}]
            }
        })

        for example in examples:
            blocks.append({
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{"type": "text", "text": {"content": example}}],
                    "language": "text"
                }
            })

    return blocks

def create_email_blocks(subject: str, sender: str, recipient: str, body: str, date: str = None) -> list:
    """
    Create Notion blocks for email content.
    :param subject: Email subject line.
    :param sender: Email sender.
    :param recipient: Email recipient.
    :param body: Email body content.
    :param date: Optional email date.
    :return: List of Notion block objects.
    """
    blocks = []

    # Add heading with subject
    blocks.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": f"📧 {subject}"}}]
        }
    })

    # Add email metadata
    metadata = f"**From:** {sender}\n**To:** {recipient}"
    if date:
        metadata += f"\n**Date:** {date}"

    blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": metadata}}]
        }
    })

    # Add separator
    blocks.append({
        "object": "block",
        "type": "divider",
        "divider": {}
    })

    # Add body content
    body_paragraphs = body.split('\n\n')
    for paragraph in body_paragraphs:
        if paragraph.strip():
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": paragraph.strip()}}]
                }
            })

    return blocks

async def handle_add_todo(arguments: dict) -> Sequence[TextContent | EmbeddedResource]:
    """
    Handle adding a new to-do.
    Args:
        arguments (dict): A dictionary containing the task details.
    Returns:
        Sequence[TextContent | EmbeddedResource]: A sequence containing the result of the operation, either a success message or an error message.
    Raises:
        ValueError: If the arguments are not a dictionary or if the task is not provided.
    """
    if not isinstance(arguments, dict):
        raise ValueError("Invalid arguments")
    
    task = arguments.get("task")
    
    if not task:
        raise ValueError("Task is required")
    
    try:
        result = await create_todo_on_page(task)
        return [
            TextContent(
                type="text",
                text=f"Added todo: {task} in the Task Integration Page"
            )
        ]
    except httpx.HTTPError as e:
        logging.error(f"Notion API error: {str(e)}")
        return [
            TextContent(
                type="text",
                text=f"Error adding todo: {str(e)}\nPlease make sure your Notion integration is properly set up and has access to the database."
            )
        ]
    
async def handle_show_all_todos() -> Sequence[TextContent | EmbeddedResource]:
    """
    Handle showing all to-do items.

    Fetches all to-do items from a specific page and returns them as a list of 
    TextContent objects. If no to-do items are found, returns a message indicating 
    that no items were found.

    Returns:
        Sequence[TextContent | EmbeddedResource]: A list containing a TextContent 
        object with the to-do items or a message indicating no items were found.
    """
    todos = await fetch_todos_on_page(PAGE_ID)
    if todos:
        todo_list = "\n".join([
            f"- {todo['task_id']}: {todo['text']} (Completed: {'Yes' if todo['checked'] else 'No'})"
            for todo in todos
        ])
        return [
            TextContent(
                type="text",
                text=f"Here are the todo items in the Task Integration Page:\n{todo_list}"
            )
        ]
    else:
        return [
            TextContent(
                type="text",
                text="No todo items found in the Task Integration Page."
            )
        ]

async def handle_complete_todo(arguments: dict) -> Sequence[TextContent | EmbeddedResource]:
    """
    Handle completing a to-do item.
    
    Args:
        arguments (dict): A dictionary containing the task ID.
        
    Returns:
        Sequence[TextContent | EmbeddedResource]: A sequence containing the result of the operation, either a success message or an error message.
        
    Raises:
        ValueError: If the arguments are not a dictionary or if the task ID is not provided.
        httpx.HTTPStatusError: If the request to the Notion API fails.
    """
    if not isinstance(arguments, dict):
        raise ValueError("Invalid arguments")
    
    task_id = arguments.get("task_id")
    
    if not task_id:
        raise ValueError("Task_ID is required")
    
    try:
        await complete_todo_on_page(task_id)
        return [
            TextContent(
                type="text",
                text=f"Marked todo as complete (Task_ID: {task_id})"
            )
        ]
    except httpx.HTTPError as e:
        logging.error(f"Notion API error: {str(e)}")
        return [
            TextContent(
                type="text",
                text=f"Error completing todo: {str(e)}\nPlease make sure your Notion integration is properly set up and has access to the database."
            )
        ]

async def handle_read_page(arguments: dict) -> Sequence[TextContent | EmbeddedResource]:
    """
    Handle reading and summarizing page content.
    """
    if not isinstance(arguments, dict):
        raise ValueError("Invalid arguments")

    # page_id = arguments.get("page_id")
    # todos = await fetch_todos_on_page(PAGE_ID)
    # if not page_id:
    #     raise ValueError("page_id is required")

    try:
        page_content = await fetch_page_content(PAGE_ID)
        text_summary = extract_text_from_blocks(page_content["blocks"])

        page_title = "Unknown Page"
        if page_content["page_metadata"].get("properties", {}).get("title"):
            title_prop = page_content["page_metadata"]["properties"]["title"]
            if title_prop.get("title"):
                page_title = "".join([t["plain_text"] for t in title_prop["title"]])

        return [
            TextContent(
                type="text",
                text=f"📄 **{page_title}**\n\n{text_summary}" if text_summary else f"📄 **{page_title}**\n\nNo content found on this page."
            )
        ]
    except httpx.HTTPError as e:
        logging.error(f"Notion API error: {str(e)}")
        return [
            TextContent(
                type="text",
                text=f"Error reading page: {str(e)}"
            )
        ]

async def handle_write_chat_summary(arguments: dict) -> Sequence[TextContent | EmbeddedResource]:
    """
    Handle writing Claude chat summaries to a page.
    """
    if not isinstance(arguments, dict):
        raise ValueError("Invalid arguments")

    page_id = arguments.get("page_id", PAGE_ID)
    summary = arguments.get("summary")
    key_points = arguments.get("key_points", [])
    examples = arguments.get("examples", [])

    if not summary:
        raise ValueError("summary is required")

    try:
        blocks = create_claude_chat_summary_blocks(summary, key_points, examples)
        await add_content_to_page(page_id, blocks)

        return [
            TextContent(
                type="text",
                text=f"✅ Claude chat summary added to page successfully!"
            )
        ]
    except httpx.HTTPError as e:
        logging.error(f"Notion API error: {str(e)}")
        return [
            TextContent(
                type="text",
                text=f"Error writing chat summary: {str(e)}"
            )
        ]

async def handle_add_email(arguments: dict) -> Sequence[TextContent | EmbeddedResource]:
    """
    Handle adding email content to a page.
    """
    if not isinstance(arguments, dict):
        raise ValueError("Invalid arguments")

    page_id = arguments.get("page_id", PAGE_ID)
    subject = arguments.get("subject")
    sender = arguments.get("sender")
    recipient = arguments.get("recipient")
    body = arguments.get("body")
    date = arguments.get("date")

    if not all([subject, sender, recipient, body]):
        raise ValueError("subject, sender, recipient, and body are required")

    try:
        blocks = create_email_blocks(subject, sender, recipient, body, date)
        await add_content_to_page(page_id, blocks)

        return [
            TextContent(
                type="text",
                text=f"✅ Email '{subject}' added to page successfully!"
            )
        ]
    except httpx.HTTPError as e:
        logging.error(f"Notion API error: {str(e)}")
        return [
            TextContent(
                type="text",
                text=f"Error adding email: {str(e)}"
            )
        ]

async def handle_create_subpage(arguments: dict) -> Sequence[TextContent | EmbeddedResource]:
    """
    Handle creating a new subpage.
    """
    if not isinstance(arguments, dict):
        raise ValueError("Invalid arguments")

    parent_page_id = arguments.get("parent_page_id", PAGE_ID)
    title = arguments.get("title")
    initial_content = arguments.get("initial_content", "")

    if not title:
        raise ValueError("title is required")

    try:
        content_blocks = []
        if initial_content:
            content_blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": initial_content}}]
                }
            })

        result = await create_subpage(parent_page_id, title, content_blocks)
        page_id = result.get("id")

        return [
            TextContent(
                type="text",
                text=f"✅ Subpage '{title}' created successfully! Page ID: {page_id}"
            )
        ]
    except httpx.HTTPError as e:
        logging.error(f"Notion API error: {str(e)}")
        return [
            TextContent(
                type="text",
                text=f"Error creating subpage: {str(e)}"
            )
        ]

async def handle_add_content(arguments: dict) -> Sequence[TextContent | EmbeddedResource]:
    """
    Handle adding detailed content to a page.
    """
    if not isinstance(arguments, dict):
        raise ValueError("Invalid arguments")

    page_id = arguments.get("page_id", PAGE_ID)
    content_type = arguments.get("content_type", "paragraph")
    content = arguments.get("content")

    if not content:
        raise ValueError("content is required")

    try:
        blocks = []

        if content_type == "paragraph":
            for para in content.split('\n\n'):
                if para.strip():
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": para.strip()}}]
                        }
                    })
        elif content_type == "heading":
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": content}}]
                }
            })
        elif content_type == "bullet_list":
            for item in content.split('\n'):
                if item.strip():
                    blocks.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": item.strip()}}]
                        }
                    })
        elif content_type == "code":
            blocks.append({
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{"type": "text", "text": {"content": content}}],
                    "language": "text"
                }
            })
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": content}}]
                }
            })

        await add_content_to_page(page_id, blocks)

        return [
            TextContent(
                type="text",
                text=f"✅ Content added to page successfully!"
            )
        ]
    except httpx.HTTPError as e:
        logging.error(f"Notion API error: {str(e)}")
        return [
            TextContent(
                type="text",
                text=f"Error adding content: {str(e)}"
            )
        ]

@server.list_tools()
async def list_tools() -> list[Tool]:
    """
    List all available tools.

    Returns:
        list[Tool]: A list of available tools.
    """
    return [
        Tool(
            name="add_todo",
            description="Add a new todo item",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The todo task description",
                    },

                },
                "required": ["task"]
            }
        ),
        Tool(
            name="show_all_todos",
            description="Show all todo items from Notion.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="complete_todo",
            description="Mark a todo item as completed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The task_id of the todo task to mark as complete."
                    }
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="read_page",
            description="Read and summarize content from a Notion page.",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_id": {
                        "type": "string",
                        "description": "The ID of the Notion page to read."
                    }
                },
                "required": ["page_id"]
            }
        ),
        Tool(
            name="write_chat_summary",
            description="Write a Claude chat summary to a Notion page with key points and examples.",
            inputSchema={
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "Brief summary of the conversation."
                    },
                    "key_points": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of key points from the conversation."
                    },
                    "examples": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of code examples or illustrations."
                    },
                    "page_id": {
                        "type": "string",
                        "description": "Optional page ID. Uses default PAGE_ID if not provided."
                    }
                },
                "required": ["summary"]
            }
        ),
        Tool(
            name="add_email",
            description="Add email content to a Notion page with proper formatting.",
            inputSchema={
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "Email subject line."
                    },
                    "sender": {
                        "type": "string",
                        "description": "Email sender address."
                    },
                    "recipient": {
                        "type": "string",
                        "description": "Email recipient address."
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body content."
                    },
                    "date": {
                        "type": "string",
                        "description": "Optional email date."
                    },
                    "page_id": {
                        "type": "string",
                        "description": "Optional page ID. Uses default PAGE_ID if not provided."
                    }
                },
                "required": ["subject", "sender", "recipient", "body"]
            }
        ),
        Tool(
            name="create_subpage",
            description="Create a new subpage under a parent page.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the new subpage."
                    },
                    "initial_content": {
                        "type": "string",
                        "description": "Optional initial content for the subpage."
                    },
                    "parent_page_id": {
                        "type": "string",
                        "description": "Optional parent page ID. Uses default PAGE_ID if not provided."
                    }
                },
                "required": ["title"]
            }
        ),
        Tool(
            name="add_content",
            description="Add detailed content to a Notion page with various formatting options.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Content to add to the page."
                    },
                    "content_type": {
                        "type": "string",
                        "enum": ["paragraph", "heading", "bullet_list", "code"],
                        "description": "Type of content formatting (default: paragraph)."
                    },
                    "page_id": {
                        "type": "string",
                        "description": "Optional page ID. Uses default PAGE_ID if not provided."
                    }
                },
                "required": ["content"]
            }
        ),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | EmbeddedResource]:
    """
    Handle tool calls for Notion management.

    Args:
        name (str): The name of the tool to call.
        arguments (Any): The arguments to pass to the tool.

    Returns:
        Sequence[TextContent | EmbeddedResource]: The result of the tool call, either a success message or an error message.
    """

    if name == "add_todo":
        return await handle_add_todo(arguments)

    elif name == "show_all_todos" or name == "show_todos":
        return await handle_show_all_todos()

    elif name == "complete_todo":
        return await handle_complete_todo(arguments)

    elif name == "read_page":
        return await handle_read_page(arguments)

    elif name == "write_chat_summary":
        return await handle_write_chat_summary(arguments)

    elif name == "add_email":
        return await handle_add_email(arguments)

    elif name == "create_subpage":
        return await handle_create_subpage(arguments)

    elif name == "add_content":
        return await handle_add_content(arguments)

    raise ValueError(f"Unknown tool: {name}")

async def main():
    """Main entry point for the server"""
    from mcp.server.stdio import stdio_server
    
    if not NOTION_TOKEN or not PAGE_ID:
        raise ValueError("NOTION_TOKEN and PAGE_ID environment variables are required")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())