"""
Azure OpenAI client for chat functionality
Handles function calling with tool definitions for Matt Deakyne API endpoints
"""
from openai import AzureOpenAI
from typing import List, Dict, Any, Optional
import os
import json
import time
import uuid
from posthog_client import get_posthog_client


class AzureOpenAIClient:
    """Client wrapper for Azure OpenAI with function calling support"""

    def __init__(self):
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

        if not api_key or not endpoint:
            # Allow initialization without credentials for development/testing
            # The client will raise a helpful error if chat_completion is called
            self.client = None
        else:
            self.client = AzureOpenAI(
                api_key=api_key,
                azure_endpoint=endpoint,
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
            )

        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")
        self.tools = self._define_tools()
        self.system_prompt = self._get_system_prompt()

        # PostHog analytics
        self.analytics_enabled = os.getenv("LLM_ANALYTICS_ENABLED", "true").lower() == "true"
        self.posthog = get_posthog_client() if self.analytics_enabled else None

        # Pricing configuration (per 1K tokens)
        self.prompt_cost_per_1k = float(os.getenv("GPT4_PROMPT_COST_PER_1K", "0.03"))
        self.completion_cost_per_1k = float(os.getenv("GPT4_COMPLETION_COST_PER_1K", "0.06"))

    def _get_system_prompt(self) -> str:
        """System prompt for the AI assistant"""
        return """You are a helpful AI assistant that answers questions about Matt Deakyne,
a technical educator, data evangelist, and automation strategist based in Lawrence, Kansas.

You have access to various API endpoints that provide information about Matt's:
- Professional profile and summary
- Work experience and positions
- Education and degrees
- Technical skills and tools
- Core competencies
- Portfolio projects
- Hobbies and interests
- Reading list
- Core principles and philosophy

When answering questions, use the available tools to gather accurate information.
Provide concise, helpful responses that directly answer the user's question.
If you need information from multiple endpoints, call them as needed.
Always base your answers on the actual data from the API endpoints."""

    def _define_tools(self) -> List[Dict]:
        """Define function schemas for all available API endpoints"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_profile",
                    "description": "Get Matt Deakyne's basic profile information including name, location, contact details, personal brand, headline, and professional summary",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_summary",
                    "description": "Get Matt's professional summary, mission statement, and core strengths",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_experience",
                    "description": "Get Matt's complete work experience including all positions, companies, dates, and achievements",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_education",
                    "description": "Get Matt's educational background including all degrees, institutions, years, and GPAs",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_skills",
                    "description": "Get Matt's technical skills including programming languages, frameworks, data platforms, automation platforms, tools, and specializations",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_competencies",
                    "description": "Get Matt's core competencies and leadership areas including education leadership, data and automation, evangelism and community, and collaboration skills",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_projects",
                    "description": "Get Matt's portfolio projects with descriptions and technologies used",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_hobbies",
                    "description": "Get Matt's hobbies and interests including creative projects, physical activities, and family/community involvement",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_books",
                    "description": "Get Matt's reading list including currently reading, recent reads, and books up next",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_principles",
                    "description": "Get Matt's core principles, beliefs, and professional philosophy",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        ]

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tool_executor: Any,
        max_iterations: int = 5,
        email: str = "anonymous",
        session_id: Optional[str] = None
    ) -> tuple[str, int]:
        """
        Execute chat completion with function calling support

        Args:
            messages: Conversation history (list of {role, content} dicts)
            tool_executor: ToolExecutor instance for making API calls
            max_iterations: Maximum number of function calling iterations
            email: User email for analytics tracking (default: "anonymous")
            session_id: Conversation session ID for analytics tracking (optional)

        Returns:
            Tuple of (assistant_response, total_tokens_used)

        Raises:
            RuntimeError: If Azure OpenAI client is not configured
        """
        if self.client is None:
            raise RuntimeError(
                "Azure OpenAI client is not configured. "
                "Please set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT environment variables."
            )

        # Generate trace ID for linking events
        trace_id = str(uuid.uuid4())
        conversation_start_time = time.time()

        # Prepend system message
        full_messages = [{"role": "system", "content": self.system_prompt}] + messages

        total_tokens = 0
        iterations = 0

        while iterations < max_iterations:
            iterations += 1

            # Call Azure OpenAI
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=full_messages,
                tools=self.tools,
                tool_choice="auto"
            )

            # Track token usage
            if response.usage:
                total_tokens += response.usage.total_tokens

            message = response.choices[0].message

            # If no tool calls, we have our final answer
            if not message.tool_calls:
                # Capture final generation event
                if self.posthog and self.analytics_enabled:
                    self._capture_generation_event(
                        trace_id=trace_id,
                        email=email,
                        session_id=session_id,
                        messages=messages,
                        response_content=message.content or "",
                        prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                        completion_tokens=response.usage.completion_tokens if response.usage else 0,
                        total_tokens=total_tokens,
                        latency_ms=int((time.time() - conversation_start_time) * 1000),
                        tools_called=[]
                    )
                return message.content or "", total_tokens

            # Add assistant message with tool calls to history
            full_messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]
            })

            # Execute each tool call
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}

                # Execute the tool via tool_executor
                try:
                    result = await tool_executor.execute(function_name, function_args)
                    function_response = json.dumps(result)
                except Exception as e:
                    function_response = json.dumps({"error": str(e)})

                # Add function response to messages
                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": function_response
                })

        # If we hit max iterations, return what we have
        return "I apologize, but I encountered an issue processing your request. Please try rephrasing your question.", total_tokens

    def _capture_generation_event(
        self,
        trace_id: str,
        email: str,
        session_id: Optional[str],
        messages: List[Dict[str, str]],
        response_content: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        latency_ms: int,
        tools_called: List[str]
    ) -> None:
        """Capture $ai_generation event to PostHog"""
        # Calculate costs
        prompt_cost = (prompt_tokens / 1000) * self.prompt_cost_per_1k
        completion_cost = (completion_tokens / 1000) * self.completion_cost_per_1k
        total_cost = prompt_cost + completion_cost

        # Get user message (last message in history)
        user_message = messages[-1]["content"] if messages else ""

        # Build event properties
        properties = {
            "$process_person_profile": False,
            "model": self.deployment,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "prompt_cost": prompt_cost,
            "completion_cost": completion_cost,
            "total_cost": total_cost,
            "latency_ms": latency_ms,
            "trace_id": trace_id,
            "tools_called": tools_called,
            "tool_call_count": len(tools_called),
            "input": user_message,
            "output": response_content,
            "input_length": len(user_message),
            "output_length": len(response_content),
            "endpoint": "/api/chat",
        }

        if session_id:
            properties["session_id"] = session_id

        self.posthog.capture(
            distinct_id=email,
            event="$ai_generation",
            properties=properties
        )
