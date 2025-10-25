"""
Tool executor for chat endpoint
Executes function calls by invoking actual API endpoints internally
"""
from typing import Dict, Any
import httpx
import os


class ToolExecutor:
    """Executes tool calls by making internal HTTP requests to API endpoints"""

    def __init__(self, bearer_token: str):
        """
        Initialize tool executor with authentication

        Args:
            bearer_token: JWT token for API authentication
        """
        self.token = bearer_token
        self.base_url = os.getenv("INTERNAL_API_BASE_URL", "http://localhost:8000")
        self.endpoint_map = {
            "get_profile": "/api/profile",
            "get_summary": "/api/summary",
            "get_experience": "/api/experience",
            "get_education": "/api/education",
            "get_skills": "/api/skills",
            "get_competencies": "/api/competencies",
            "get_projects": "/api/projects",
            "get_hobbies": "/api/hobbies",
            "get_books": "/api/books",
            "get_principles": "/api/principles",
        }

    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool call by making an internal API request

        Args:
            tool_name: Name of the tool/function to execute
            arguments: Function arguments (currently unused as all endpoints are GET with no params)

        Returns:
            API response as dictionary

        Raises:
            ValueError: If tool_name is not recognized
            httpx.HTTPError: If API request fails
        """
        if tool_name not in self.endpoint_map:
            raise ValueError(f"Unknown tool: {tool_name}")

        endpoint = self.endpoint_map[tool_name]
        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
