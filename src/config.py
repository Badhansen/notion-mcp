from mcp.server import Server
from dotenv import load_dotenv
from pathlib import Path
import os


class EnvironmentConfig:
    def __init__(self):
        self._load_env_file()
        self._load_variables()
        self._create_headers()

    def _load_env_file(self):
        """Load .env file from project root"""
        project_root = Path(__file__).resolve().parent.parent
        env_path = project_root / '.env'

        if not env_path.exists():
            raise FileNotFoundError(f"No .env file found at {env_path}")

        load_dotenv(env_path)

    def _load_variables(self):
        """Load environment variables"""
        self.NOTION_TOKEN = os.getenv("NOTION_TOKEN")
        self.DATABSE_ID = os.getenv("DATABSE_ID")
        self.PAGE_ID = os.getenv("PAGE_ID")
        self.NOTION_VERSION = os.getenv("NOTION_VERSION")
        self.NOTION_BASE_URL = os.getenv("NOTION_BASE_URL")

    def _create_headers(self):
        """Create Notion API headers"""
        self.headers = {
            "Authorization": f"Bearer {self.NOTION_TOKEN}",
            "Content-Type": "application/json",
            "Notion-Version": self.NOTION_VERSION
        }

    def validate(self):
        """Validate required environment variables"""
        if not self.NOTION_TOKEN or not self.PAGE_ID:
            raise ValueError("NOTION_TOKEN and PAGE_ID environment variables are required")
        return True


# Create global config instance
config = EnvironmentConfig()
config.validate()

# Create a named server
server = Server("notion-mcp")