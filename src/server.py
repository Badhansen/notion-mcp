from mcp.types import Tool, TextContent, EmbeddedResource
from typing import Any, Sequence
import logging
import httpx

# Import config and server from config module
from config import config, server

# Setup logging configuration (separate from environment config)
logging.basicConfig(level=logging.INFO)


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
                f"{config.NOTION_BASE_URL}/blocks/{page_id}/children",
                headers=config.headers,
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
    if not config.PAGE_ID:
        raise ValueError("PAGE_ID is not set in the .env file.")
    
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{config.NOTION_BASE_URL}/blocks/{config.PAGE_ID}/children",
            headers=config.headers,
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
    todos = await fetch_todos_on_page(config.PAGE_ID)

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
                f"{config.NOTION_BASE_URL}/blocks/{task_id}",
                headers=config.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logging.info("No to-do found in the page.")
        raise ValueError(f"Error completing todo: {str(e)}")

async def handle_write_chat_summary(arguments: dict) -> Sequence[TextContent | EmbeddedResource]:
    """
    Handle writing Claude chat summaries to a Notion page.
    Args:
        arguments (dict): A dictionary containing summary details.
    Returns:
        Sequence[TextContent | EmbeddedResource]: Result of the operation.
    """
    if not isinstance(arguments, dict):
        raise ValueError("Invalid arguments")

    summary = arguments.get("summary")
    key_points = arguments.get("key_points", [])
    examples = arguments.get("examples", [])
    page_id = arguments.get("page_id")

    if not summary:
        raise ValueError("summary is required")

    # Always use the working page_id (same as todos) unless explicitly overridden
    if not page_id:
        page_id = config.PAGE_ID

    try:
        # Create blocks for the chat summary
        blocks = []

        # Generate title using Claude's understanding of the content
        title = arguments.get("title")
        if not title:
            # Create a concise title from the summary
            summary_words = summary.split()
            if len(summary_words) <= 5:
                title = summary
            else:
                # Use first meaningful part or ask user to provide title
                title = " ".join(summary_words[:5]) + "..."

        # Add heading with generated title
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": f"💬 {title}"}}]
            }
        })

        # Add timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": f"Date: {timestamp}"}
                    }
                ]
            }
        })

        # Add divider after timestamp
        blocks.append({
            "object": "block",
            "type": "divider",
            "divider": {}
        })
        # Add summary
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": summary}}]
            }
        })

        # Add key points if provided
        if key_points:
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": "Key Points"}}]
                }
            })

            for point in key_points:
                # Validate and clean the point content
                if point and isinstance(point, str):
                    clean_point = point.strip()[:2000]  # Limit length and clean
                    if clean_point:
                        blocks.append({
                            "object": "block",
                            "type": "bulleted_list_item",
                            "bulleted_list_item": {
                                "rich_text": [{"type": "text", "text": {"content": clean_point}}]
                            }
                        })

        # Add examples if provided
        if examples:
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": "Examples/Code"}}]
                }
            })

            for example in examples:
                # Validate and clean the example content
                if example and isinstance(example, str):
                    clean_example = example.strip()[:2000]  # Limit length and clean
                    if clean_example:
                        blocks.append({
                            "object": "block",
                            "type": "code",
                            "code": {
                                "rich_text": [{"type": "text", "text": {"content": clean_example}}],
                                "language": "text"
                            }
                        })

        # Add divider
        blocks.append({
            "object": "block",
            "type": "divider",
            "divider": {}
        })

        # Add the blocks to the page
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{config.NOTION_BASE_URL}/blocks/{page_id}/children",
                headers=config.headers,
                json={"children": blocks}
            )
            response.raise_for_status()

        return [
            TextContent(
                type="text",
                text=f"Chat summary added to Notion page successfully! Added {len(blocks)} blocks."
            )
        ]
    except httpx.HTTPError as e:
        error_details = f"Notion API error: {str(e)}"

        # Get detailed error response
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_body = e.response.json()
                error_details += f"\nDetailed error: {error_body}"
            except:
                error_details += f"\nResponse text: {e.response.text}"

        logging.error(error_details)

        return [
            TextContent(
                type="text",
                text=f"Error writing chat summary: {str(e)}\nPage ID used: {page_id}\nCheck console for detailed error info."
            )
        ]

async def handle_create_conversation_thread(arguments: dict) -> Sequence[TextContent | EmbeddedResource]:
    """
    Create a conversation thread with multiple related chat summaries as sub-pages.
    Args:
        arguments (dict): A dictionary containing thread details and conversations.
    Returns:
        Sequence[TextContent | EmbeddedResource]: Result of the operation.
    """
    if not isinstance(arguments, dict):
        raise ValueError("Invalid arguments")

    thread_title = arguments.get("thread_title")
    thread_description = arguments.get("thread_description", "")
    # Remove conversations array - use write_chat_summary function instead
    parent_page_id = arguments.get("parent_page_id", config.PAGE_ID)

    if not thread_title:
        raise ValueError("thread_title is required")

    # Conversations are optional - can create empty thread for future use

    try:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Create main thread page
        thread_page_data = {
            "parent": {"page_id": parent_page_id},
            "properties": {
                "title": {
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": f"🧵 {thread_title}"}
                        }
                    ]
                }
            },
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": f"Thread created: {timestamp}"},
                                "annotations": {"italic": True}
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                }
            ]
        }

        # Add thread description if provided
        if thread_description:
            thread_page_data["children"].append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": thread_description}}]
                }
            })
            thread_page_data["children"].append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })

        # Create the main thread page
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config.NOTION_BASE_URL}/pages",
                headers=config.headers,
                json=thread_page_data
            )
            response.raise_for_status()
            thread_page = response.json()
            thread_page_id = thread_page.get("id")

        return [
            TextContent(
                type="text",
                text=f"✅ Thread page '{thread_title}' created successfully!\n"
                     f"📄 Thread page ID: {thread_page_id}\n"
                     f"💡 Use write_chat_summary with this page_id to add conversation summaries"
            )
        ]

    except httpx.HTTPError as e:
        logging.error(f"Notion API error: {str(e)}")
        return [
            TextContent(
                type="text",
                text=f"Error creating conversation thread: {str(e)}\n"
                     f"Please make sure your Notion integration is properly set up and has access to the page."
            )
        ]

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
        await create_todo_on_page(task)
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
    todos = await fetch_todos_on_page(config.PAGE_ID)
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
        Tool(
            name="write_chat_summary",
            description="Write a Claude chat summary to Notion with key points and examples",
            inputSchema={
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "Brief summary of the conversation"
                    },
                    "title": {
                        "type": "string",
                        "description": "Optional custom title for the chat summary (if not provided, will be generated from summary)"
                    },
                    "key_points": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of key points from the conversation"
                    },
                    "examples": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of examples or important details"
                    },
                    "page_id": {
                        "type": "string",
                        "description": "Optional Notion page ID (uses default if not provided)"
                    }
                },
                "required": ["summary"]
            }
        ),
        Tool(
            name="create_conversation_thread",
            description="Create a thread page for organizing conversation summaries. Use write_chat_summary to add summaries to this thread.",
            inputSchema={
                "type": "object",
                "properties": {
                    "thread_title": {
                        "type": "string",
                        "description": "Title for the conversation thread page"
                    },
                    "thread_description": {
                        "type": "string",
                        "description": "Optional description for the conversation thread"
                    },
                    "parent_page_id": {
                        "type": "string",
                        "description": "Optional parent page ID (uses default if not provided)"
                    }
                },
                "required": ["thread_title"]
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

    elif name == "write_chat_summary":
        return await handle_write_chat_summary(arguments)

    elif name == "create_conversation_thread":
        return await handle_create_conversation_thread(arguments)

    raise ValueError(f"Unknown tool: {name}")

async def main():
    """Main entry point for the server"""
    from mcp.server.stdio import stdio_server
    
    if not config.NOTION_TOKEN or not config.PAGE_ID:
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