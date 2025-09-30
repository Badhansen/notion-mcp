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
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | EmbeddedResource]:
    """
    Handle tool calls for todo management.

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