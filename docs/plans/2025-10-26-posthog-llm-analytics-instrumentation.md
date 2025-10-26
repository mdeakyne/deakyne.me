# PostHog LLM Analytics Instrumentation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Instrument the `/api/chat` endpoint with PostHog LLM analytics to track AI generations, token usage, costs, latency, and tool calls for observability and optimization.

**Architecture:** Add PostHog event capture to the Azure OpenAI client (`backend/azure_openai_client.py`) to track three event types: `$ai_generation` (LLM completions), `$ai_tool_call` (function executions), and `$ai_error` (failures). Use trace IDs to link related events across multi-turn conversations. Calculate estimated costs using configurable per-1K-token pricing from environment variables. All events use `$process_person_profile: false` to avoid creating person profiles.

**Tech Stack:** Python 3.11+, PostHog Python SDK 3.5.0, Azure OpenAI, FastAPI

---

## Task 1: Add Environment Variables for LLM Analytics Configuration

**Files:**
- Modify: `backend/.env.example:36`

**Step 1: Add LLM analytics environment variables**

Add these lines after line 35 (after `CHAT_MAX_HISTORY_MESSAGES=20`):

```bash
# LLM Analytics
LLM_ANALYTICS_ENABLED=true
GPT4_PROMPT_COST_PER_1K=0.03
GPT4_COMPLETION_COST_PER_1K=0.06
GPT4_TURBO_PROMPT_COST_PER_1K=0.01
GPT4_TURBO_COMPLETION_COST_PER_1K=0.03
```

**Step 2: Verify changes**

Run: `cat backend/.env.example | tail -10`
Expected: See the new LLM analytics configuration section

**Step 3: Commit**

```bash
git add backend/.env.example
git commit -m "feat: add LLM analytics environment variables

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 2: Write Tests for PostHog Event Capture in Azure OpenAI Client

**Files:**
- Create: `backend/tests/test_azure_openai_analytics.py`

**Step 1: Write the failing test for $ai_generation event capture**

Create the test file with this content:

```python
"""
Tests for Azure OpenAI client PostHog analytics instrumentation
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, call
import json
import os
import sys

# Add backend directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from azure_openai_client import AzureOpenAIClient


@pytest.fixture
def mock_openai_response():
    """Mock Azure OpenAI completion response"""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Matt is a technical educator."
    mock_response.choices[0].message.tool_calls = None
    mock_response.usage = Mock()
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_response.usage.total_tokens = 150
    return mock_response


@pytest.fixture
def mock_tool_executor():
    """Mock tool executor"""
    executor = AsyncMock()
    executor.execute = AsyncMock(return_value={"name": "Matt Deakyne"})
    return executor


class TestAIGenerationEventCapture:
    """Tests for $ai_generation event tracking"""

    @patch("azure_openai_client.get_posthog_client")
    @patch.dict(os.environ, {
        "AZURE_OPENAI_API_KEY": "test-key",
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        "LLM_ANALYTICS_ENABLED": "true",
        "GPT4_PROMPT_COST_PER_1K": "0.03",
        "GPT4_COMPLETION_COST_PER_1K": "0.06"
    })
    @pytest.mark.asyncio
    async def test_captures_ai_generation_event(
        self,
        mock_get_posthog,
        mock_openai_response,
        mock_tool_executor
    ):
        """Test that successful chat completion captures $ai_generation event"""
        # Setup
        mock_posthog = Mock()
        mock_get_posthog.return_value = mock_posthog

        client = AzureOpenAIClient()

        with patch.object(client.client.chat.completions, 'create', return_value=mock_openai_response):
            # Execute
            response, tokens = await client.chat_completion(
                messages=[{"role": "user", "content": "Who is Matt?"}],
                tool_executor=mock_tool_executor,
                email="test@example.com",
                session_id="session-123"
            )

        # Assert: PostHog capture was called
        assert mock_posthog.capture.called
        capture_call = mock_posthog.capture.call_args

        # Verify event structure
        assert capture_call.kwargs["distinct_id"] == "test@example.com"
        assert capture_call.kwargs["event"] == "$ai_generation"

        props = capture_call.kwargs["properties"]
        assert props["$process_person_profile"] is False
        assert props["model"] == "gpt-4"
        assert props["prompt_tokens"] == 100
        assert props["completion_tokens"] == 50
        assert props["total_tokens"] == 150
        assert "latency_ms" in props
        assert props["latency_ms"] > 0
        assert props["session_id"] == "session-123"
        assert "trace_id" in props

    @patch("azure_openai_client.get_posthog_client")
    @patch.dict(os.environ, {
        "AZURE_OPENAI_API_KEY": "test-key",
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        "GPT4_PROMPT_COST_PER_1K": "0.03",
        "GPT4_COMPLETION_COST_PER_1K": "0.06"
    })
    @pytest.mark.asyncio
    async def test_cost_calculation(
        self,
        mock_get_posthog,
        mock_openai_response,
        mock_tool_executor
    ):
        """Test that cost is calculated correctly"""
        mock_posthog = Mock()
        mock_get_posthog.return_value = mock_posthog

        client = AzureOpenAIClient()

        with patch.object(client.client.chat.completions, 'create', return_value=mock_openai_response):
            await client.chat_completion(
                messages=[{"role": "user", "content": "Who is Matt?"}],
                tool_executor=mock_tool_executor,
                email="test@example.com",
                session_id="session-123"
            )

        props = mock_posthog.capture.call_args.kwargs["properties"]

        # Cost calculation: (100/1000)*0.03 + (50/1000)*0.06 = 0.003 + 0.003 = 0.006
        assert props["prompt_cost"] == pytest.approx(0.003, rel=1e-6)
        assert props["completion_cost"] == pytest.approx(0.003, rel=1e-6)
        assert props["total_cost"] == pytest.approx(0.006, rel=1e-6)

    @patch("azure_openai_client.get_posthog_client")
    @patch.dict(os.environ, {
        "AZURE_OPENAI_API_KEY": "test-key",
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        "LLM_ANALYTICS_ENABLED": "false"
    })
    @pytest.mark.asyncio
    async def test_analytics_disabled(
        self,
        mock_get_posthog,
        mock_openai_response,
        mock_tool_executor
    ):
        """Test that analytics can be disabled via environment variable"""
        mock_posthog = Mock()
        mock_get_posthog.return_value = mock_posthog

        client = AzureOpenAIClient()

        with patch.object(client.client.chat.completions, 'create', return_value=mock_openai_response):
            await client.chat_completion(
                messages=[{"role": "user", "content": "Who is Matt?"}],
                tool_executor=mock_tool_executor,
                email="test@example.com",
                session_id="session-123"
            )

        # Should not capture when disabled
        assert not mock_posthog.capture.called


class TestToolCallEventCapture:
    """Tests for $ai_tool_call event tracking"""

    @patch("azure_openai_client.get_posthog_client")
    @patch.dict(os.environ, {
        "AZURE_OPENAI_API_KEY": "test-key",
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        "LLM_ANALYTICS_ENABLED": "true"
    })
    @pytest.mark.asyncio
    async def test_captures_tool_call_event(
        self,
        mock_get_posthog,
        mock_tool_executor
    ):
        """Test that tool calls generate $ai_tool_call events"""
        mock_posthog = Mock()
        mock_get_posthog.return_value = mock_posthog

        # Mock response with tool call
        mock_response_with_tool = Mock()
        mock_response_with_tool.choices = [Mock()]
        mock_response_with_tool.choices[0].message.content = None

        # Create tool call
        tool_call = Mock()
        tool_call.id = "call-123"
        tool_call.function.name = "get_profile"
        tool_call.function.arguments = "{}"
        mock_response_with_tool.choices[0].message.tool_calls = [tool_call]
        mock_response_with_tool.usage = Mock(total_tokens=100)

        # Mock final response without tool calls
        mock_final_response = Mock()
        mock_final_response.choices = [Mock()]
        mock_final_response.choices[0].message.content = "Matt is a technical educator."
        mock_final_response.choices[0].message.tool_calls = None
        mock_final_response.usage = Mock(total_tokens=50)

        client = AzureOpenAIClient()

        with patch.object(
            client.client.chat.completions,
            'create',
            side_effect=[mock_response_with_tool, mock_final_response]
        ):
            await client.chat_completion(
                messages=[{"role": "user", "content": "Who is Matt?"}],
                tool_executor=mock_tool_executor,
                email="test@example.com",
                session_id="session-123"
            )

        # Should have 2 calls: 1 for tool call, 1 for final generation
        assert mock_posthog.capture.call_count == 2

        # First call should be $ai_tool_call
        tool_call_event = mock_posthog.capture.call_args_list[0].kwargs
        assert tool_call_event["event"] == "$ai_tool_call"
        assert tool_call_event["properties"]["tool_name"] == "get_profile"
        assert tool_call_event["properties"]["tool_args"] == "{}"
        assert "tool_latency_ms" in tool_call_event["properties"]
        assert "trace_id" in tool_call_event["properties"]


class TestErrorTracking:
    """Tests for $ai_error event tracking"""

    @patch("azure_openai_client.get_posthog_client")
    @patch.dict(os.environ, {
        "AZURE_OPENAI_API_KEY": "test-key",
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        "LLM_ANALYTICS_ENABLED": "true"
    })
    @pytest.mark.asyncio
    async def test_captures_tool_execution_error(
        self,
        mock_get_posthog,
        mock_tool_executor
    ):
        """Test that tool execution errors are tracked"""
        mock_posthog = Mock()
        mock_get_posthog.return_value = mock_posthog

        # Mock tool executor to raise error
        mock_tool_executor.execute = AsyncMock(side_effect=Exception("API Error"))

        # Mock response with tool call
        mock_response_with_tool = Mock()
        mock_response_with_tool.choices = [Mock()]
        mock_response_with_tool.choices[0].message.content = None

        tool_call = Mock()
        tool_call.id = "call-123"
        tool_call.function.name = "get_profile"
        tool_call.function.arguments = "{}"
        mock_response_with_tool.choices[0].message.tool_calls = [tool_call]
        mock_response_with_tool.usage = Mock(total_tokens=100)

        # Mock final response
        mock_final_response = Mock()
        mock_final_response.choices = [Mock()]
        mock_final_response.choices[0].message.content = "Error occurred"
        mock_final_response.choices[0].message.tool_calls = None
        mock_final_response.usage = Mock(total_tokens=50)

        client = AzureOpenAIClient()

        with patch.object(
            client.client.chat.completions,
            'create',
            side_effect=[mock_response_with_tool, mock_final_response]
        ):
            await client.chat_completion(
                messages=[{"role": "user", "content": "Who is Matt?"}],
                tool_executor=mock_tool_executor,
                email="test@example.com",
                session_id="session-123"
            )

        # Should capture error event
        error_calls = [
            call for call in mock_posthog.capture.call_args_list
            if call.kwargs["event"] == "$ai_error"
        ]
        assert len(error_calls) == 1

        error_event = error_calls[0].kwargs
        assert error_event["properties"]["error_type"] == "Exception"
        assert error_event["properties"]["error_message"] == "API Error"
        assert error_event["properties"]["tool_name"] == "get_profile"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_azure_openai_analytics.py -v`
Expected: FAIL - `chat_completion()` missing required parameters `email` and `session_id`

**Step 3: Commit**

```bash
git add backend/tests/test_azure_openai_analytics.py
git commit -m "test: add PostHog LLM analytics instrumentation tests

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 3: Update Azure OpenAI Client Signature to Accept Analytics Parameters

**Files:**
- Modify: `backend/azure_openai_client.py:179-184`

**Step 1: Update chat_completion method signature**

Change lines 179-184 from:

```python
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tool_executor: Any,
        max_iterations: int = 5
    ) -> tuple[str, int]:
```

To:

```python
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tool_executor: Any,
        max_iterations: int = 5,
        email: str = "anonymous",
        session_id: Optional[str] = None
    ) -> tuple[str, int]:
```

**Step 2: Update docstring**

Change lines 185-197 from:

```python
        """
        Execute chat completion with function calling support

        Args:
            messages: Conversation history (list of {role, content} dicts)
            tool_executor: ToolExecutor instance for making API calls
            max_iterations: Maximum number of function calling iterations

        Returns:
            Tuple of (assistant_response, total_tokens_used)

        Raises:
            RuntimeError: If Azure OpenAI client is not configured
        """
```

To:

```python
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
```

**Step 3: Run test to verify signature updated**

Run: `cd backend && pytest tests/test_azure_openai_analytics.py::TestAIGenerationEventCapture::test_captures_ai_generation_event -v`
Expected: FAIL - `get_posthog_client` not imported, method doesn't capture events

**Step 4: Commit**

```bash
git add backend/azure_openai_client.py
git commit -m "feat: add email and session_id parameters to chat_completion

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 4: Import Dependencies and Initialize PostHog Client in Azure OpenAI Client

**Files:**
- Modify: `backend/azure_openai_client.py:1-31`

**Step 1: Add imports**

Change lines 5-8 from:

```python
from openai import AzureOpenAI
from typing import List, Dict, Any, Optional
import os
import json
```

To:

```python
from openai import AzureOpenAI
from typing import List, Dict, Any, Optional
import os
import json
import time
import uuid
from backend.posthog_client import get_posthog_client
```

**Step 2: Add PostHog client and pricing configuration to __init__**

Change lines 14-31 from:

```python
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
```

To:

```python
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
```

**Step 3: Run test to verify imports work**

Run: `cd backend && pytest tests/test_azure_openai_analytics.py::TestAIGenerationEventCapture::test_captures_ai_generation_event -v`
Expected: FAIL - PostHog capture not called (analytics code not implemented yet)

**Step 4: Commit**

```bash
git add backend/azure_openai_client.py
git commit -m "feat: initialize PostHog client and pricing config in Azure OpenAI client

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 5: Implement $ai_generation Event Capture

**Files:**
- Modify: `backend/azure_openai_client.py:179-271`

**Step 1: Add trace ID and timing to chat_completion method**

After line 203 (`raise RuntimeError...`), add:

```python
        # Generate trace ID for linking events
        trace_id = str(uuid.uuid4())
        conversation_start_time = time.time()
```

**Step 2: Track tool calls and capture final generation event**

Before the return statement at line 230 (`return message.content or "", total_tokens`), add:

```python
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
```

**Step 3: Add _capture_generation_event helper method**

At the end of the file (after line 271), add:

```python

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
```

**Step 4: Run test to verify generation event capture works**

Run: `cd backend && pytest tests/test_azure_openai_analytics.py::TestAIGenerationEventCapture -v`
Expected: PASS (all 3 tests in TestAIGenerationEventCapture)

**Step 5: Commit**

```bash
git add backend/azure_openai_client.py
git commit -m "feat: implement $ai_generation event capture

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 6: Implement $ai_tool_call Event Capture

**Files:**
- Modify: `backend/azure_openai_client.py:249-268`

**Step 1: Track tool calls and capture tool call events**

Change lines 249-268 from:

```python
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
```

To:

```python
            # Execute each tool call
            tools_called = []
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}

                tools_called.append(function_name)

                # Execute the tool via tool_executor
                tool_start_time = time.time()
                tool_error = None
                try:
                    result = await tool_executor.execute(function_name, function_args)
                    function_response = json.dumps(result)
                    tool_success = True
                except Exception as e:
                    function_response = json.dumps({"error": str(e)})
                    tool_success = False
                    tool_error = e

                tool_latency_ms = int((time.time() - tool_start_time) * 1000)

                # Capture tool call event
                if self.posthog and self.analytics_enabled:
                    self._capture_tool_call_event(
                        trace_id=trace_id,
                        email=email,
                        session_id=session_id,
                        tool_name=function_name,
                        tool_args=tool_call.function.arguments,
                        tool_result_size=len(function_response),
                        tool_latency_ms=tool_latency_ms,
                        tool_success=tool_success
                    )

                    # Capture error event if tool failed
                    if tool_error:
                        self._capture_error_event(
                            trace_id=trace_id,
                            email=email,
                            session_id=session_id,
                            error=tool_error,
                            tool_name=function_name
                        )

                # Add function response to messages
                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": function_response
                })
```

**Step 2: Update final generation capture to include tools_called**

Change the generation event capture before line 230 to pass `tools_called`:

```python
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
                    tools_called=[]  # No tools in final response
                )
```

**Step 3: Add _capture_tool_call_event helper method**

After the `_capture_generation_event` method, add:

```python

    def _capture_tool_call_event(
        self,
        trace_id: str,
        email: str,
        session_id: Optional[str],
        tool_name: str,
        tool_args: str,
        tool_result_size: int,
        tool_latency_ms: int,
        tool_success: bool
    ) -> None:
        """Capture $ai_tool_call event to PostHog"""
        properties = {
            "$process_person_profile": False,
            "tool_name": tool_name,
            "tool_args": tool_args,
            "tool_result_size": tool_result_size,
            "tool_latency_ms": tool_latency_ms,
            "tool_success": tool_success,
            "trace_id": trace_id,
        }

        if session_id:
            properties["session_id"] = session_id

        self.posthog.capture(
            distinct_id=email,
            event="$ai_tool_call",
            properties=properties
        )
```

**Step 4: Run test to verify tool call event capture works**

Run: `cd backend && pytest tests/test_azure_openai_analytics.py::TestToolCallEventCapture -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/azure_openai_client.py
git commit -m "feat: implement $ai_tool_call event capture

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 7: Implement $ai_error Event Capture

**Files:**
- Modify: `backend/azure_openai_client.py` (add method after _capture_tool_call_event)

**Step 1: Add _capture_error_event helper method**

After the `_capture_tool_call_event` method, add:

```python

    def _capture_error_event(
        self,
        trace_id: str,
        email: str,
        session_id: Optional[str],
        error: Exception,
        tool_name: Optional[str] = None
    ) -> None:
        """Capture $ai_error event to PostHog"""
        properties = {
            "$process_person_profile": False,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "trace_id": trace_id,
        }

        if session_id:
            properties["session_id"] = session_id

        if tool_name:
            properties["tool_name"] = tool_name

        self.posthog.capture(
            distinct_id=email,
            event="$ai_error",
            properties=properties
        )
```

**Step 2: Run test to verify error event capture works**

Run: `cd backend && pytest tests/test_azure_openai_analytics.py::TestErrorTracking -v`
Expected: PASS

**Step 3: Run all analytics tests**

Run: `cd backend && pytest tests/test_azure_openai_analytics.py -v`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add backend/azure_openai_client.py
git commit -m "feat: implement $ai_error event capture

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 8: Update Chat Endpoint to Pass Email and Session ID

**Files:**
- Modify: `backend/main.py` (chat endpoint)

**Step 1: Find the chat_completion call in main.py**

Run: `grep -n "chat_completion" backend/main.py`
Expected: Line number where azure_client.chat_completion is called

**Step 2: Read the chat endpoint implementation**

Run: `sed -n '/^@app.post.*\/api\/chat/,/^@app\./p' backend/main.py | head -100`
Expected: See the chat endpoint code

**Step 3: Update chat_completion call to pass email and session_id**

Find the line that calls:
```python
response, tokens = await azure_client.chat_completion(
    messages=messages,
    tool_executor=tool_executor
)
```

Change to:
```python
response, tokens = await azure_client.chat_completion(
    messages=messages,
    tool_executor=tool_executor,
    email=user_email,
    session_id=session_id
)
```

Note: The exact line numbers will depend on the current state of main.py. Find the call and update it.

**Step 4: Run existing chat endpoint tests**

Run: `cd backend && pytest tests/test_chat_endpoint.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add backend/main.py
git commit -m "feat: pass email and session_id to chat_completion for analytics

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 9: Add Integration Test for End-to-End Analytics Flow

**Files:**
- Modify: `backend/tests/test_chat_endpoint.py:209-210`

**Step 1: Add integration test after existing tests**

After line 209 (end of `test_chat_ai_error_handling`), add:

```python

    @patch("main.azure_client")
    @patch("main.chat_rate_limiter")
    @patch("main.get_posthog_client")
    def test_chat_captures_analytics(
        self,
        mock_get_posthog,
        mock_rate_limiter,
        mock_azure_client,
        client,
        mock_auth_token
    ):
        """Test that chat endpoint captures PostHog analytics events"""
        with patch("main.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "test@example.com"}

            mock_rate_limiter.check_rate_limit.return_value = None

            # Mock PostHog client
            mock_posthog = Mock()
            mock_get_posthog.return_value = mock_posthog

            # Configure azure_client mock to track analytics
            async def mock_chat_completion(messages, tool_executor, email, session_id):
                # Simulate analytics capture
                if hasattr(mock_azure_client, 'posthog') and mock_azure_client.posthog:
                    mock_azure_client.posthog.capture(
                        distinct_id=email,
                        event="$ai_generation",
                        properties={
                            "$process_person_profile": False,
                            "session_id": session_id,
                            "model": "gpt-4",
                        }
                    )
                return ("Response", 100)

            mock_azure_client.posthog = mock_posthog
            mock_azure_client.chat_completion = AsyncMock(side_effect=mock_chat_completion)

            response = client.post(
                "/api/chat",
                headers={"Authorization": f"Bearer {mock_auth_token}"},
                json={"message": "Who is Matt?", "session_id": "test-session-123"}
            )

            assert response.status_code == 200

            # Verify analytics was captured
            assert mock_posthog.capture.called
```

**Step 2: Run integration test**

Run: `cd backend && pytest tests/test_chat_endpoint.py::TestChatEndpointFunctionality::test_chat_captures_analytics -v`
Expected: PASS

**Step 3: Run all chat endpoint tests**

Run: `cd backend && pytest tests/test_chat_endpoint.py -v`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add backend/tests/test_chat_endpoint.py
git commit -m "test: add integration test for analytics capture in chat endpoint

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 10: Update README Documentation

**Files:**
- Modify: `README.md` (PostHog section)

**Step 1: Find PostHog section in README**

Run: `grep -n "PostHog" README.md`
Expected: Line numbers where PostHog is mentioned

**Step 2: Add LLM analytics documentation**

Find the PostHog configuration section and add:

```markdown
#### LLM Analytics

The chat endpoint automatically tracks AI generations with PostHog:

- **$ai_generation**: Chat completions with token usage, costs, latency
- **$ai_tool_call**: Function calls with execution time and results
- **$ai_error**: Errors during tool execution

Configure pricing and enable/disable tracking:

```env
LLM_ANALYTICS_ENABLED=true
GPT4_PROMPT_COST_PER_1K=0.03
GPT4_COMPLETION_COST_PER_1K=0.06
GPT4_TURBO_PROMPT_COST_PER_1K=0.01
GPT4_TURBO_COMPLETION_COST_PER_1K=0.03
```

Cost estimates are based on official OpenAI pricing and tracked per-user and per-session for observability.
```

**Step 3: Verify documentation looks correct**

Run: `grep -A 20 "LLM Analytics" README.md`
Expected: See the new documentation section

**Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add LLM analytics documentation to README

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 11: Manual Testing and Verification

**Files:**
- N/A (manual testing)

**Step 1: Start the backend server**

Run: `cd backend && source .env && python3 -m uvicorn main:app --reload`
Expected: Server starts on http://localhost:8000

**Step 2: Test chat endpoint with valid credentials**

In a new terminal:
```bash
# Get auth token first
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/request-key \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}')

# Make chat request
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"What are Matt'\''s technical skills?"}'
```

Expected: JSON response with answer about Matt's skills

**Step 3: Check PostHog for events**

1. Log into PostHog at https://us.i.posthog.com
2. Navigate to Events
3. Filter for event name: `$ai_generation`
4. Verify recent event has all expected properties:
   - model, tokens, costs, latency, trace_id, session_id
   - Full input/output text
   - $process_person_profile: false

**Step 4: Verify tool call events**

1. Filter for event name: `$ai_tool_call`
2. Verify tool calls have:
   - tool_name (e.g., "get_skills")
   - tool_latency_ms
   - trace_id matching generation event

**Step 5: Test error tracking**

Temporarily modify a tool in `backend/main.py` to raise an error, then make a chat request that triggers it. Verify `$ai_error` event appears in PostHog.

**Step 6: Document verification results**

Create a note in the commit message or project notes confirming:
- [ ] $ai_generation events appearing in PostHog
- [ ] $ai_tool_call events linked to generations via trace_id
- [ ] Cost calculations appear reasonable
- [ ] Error events captured when tools fail
- [ ] All event properties present and correct

---

## Task 12: Run Full Test Suite

**Files:**
- N/A (testing)

**Step 1: Run all backend tests**

Run: `cd backend && pytest -v`
Expected: All tests PASS

**Step 2: Check test coverage for new code**

Run: `cd backend && pytest --cov=. --cov-report=term-missing tests/test_azure_openai_analytics.py`
Expected: >90% coverage for azure_openai_client.py analytics code

**Step 3: Verify no regressions in existing tests**

Run: `cd backend && pytest tests/test_chat_endpoint.py tests/test_posthog_client.py -v`
Expected: All tests PASS

**Step 4: Document test results**

Note any failures or issues. All tests should pass before proceeding.

---

## Task 13: Final Verification and Cleanup

**Files:**
- Review all modified files

**Step 1: Review all changes**

Run: `git diff main...HEAD --stat`
Expected: See summary of all files changed

**Step 2: Verify code quality**

Run: `cd backend && python3 -m flake8 azure_openai_client.py tests/test_azure_openai_analytics.py --max-line-length=120`
Expected: No linting errors

**Step 3: Update .env.example if needed**

Verify all new environment variables are documented in `backend/.env.example`

**Step 4: Create final summary commit**

```bash
git add -A
git commit -m "feat: complete PostHog LLM analytics instrumentation

Summary of changes:
- Add $ai_generation event tracking for all chat completions
- Add $ai_tool_call event tracking for function calls
- Add $ai_error event tracking for tool failures
- Calculate estimated costs based on token usage
- Link events via trace_id for conversation debugging
- Add comprehensive test coverage
- Update documentation

Closes #21

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Success Criteria Checklist

Before considering this implementation complete, verify:

- [ ] All tests pass (`pytest -v`)
- [ ] $ai_generation events captured in PostHog with all properties
- [ ] $ai_tool_call events captured for each function call
- [ ] $ai_error events captured when tools fail
- [ ] Cost calculations accurate (manual verification against OpenAI pricing)
- [ ] Trace IDs link related events correctly
- [ ] Analytics can be disabled via LLM_ANALYTICS_ENABLED=false
- [ ] No performance degradation (PostHog calls are async)
- [ ] Documentation updated in README.md
- [ ] All environment variables in .env.example
- [ ] Code passes linting (flake8)
- [ ] Manual testing completed successfully

---

## Rollback Plan

If issues are discovered after deployment:

**Quick disable:**
```bash
# In backend/.env
LLM_ANALYTICS_ENABLED=false
```

**Full rollback:**
```bash
git revert HEAD
# Or revert to specific commit before analytics:
git revert <commit-hash>
```

---

## Future Enhancements

Ideas for follow-up work (not in scope for this plan):

1. Custom PostHog dashboards for LLM metrics
2. Cost alerts when daily/monthly thresholds exceeded
3. A/B testing support for different prompts/models
4. Embeddings tracking when that feature is added
5. User feedback/ratings correlation with generation quality
6. Automatic cost anomaly detection
7. Token usage optimization suggestions based on patterns

---

## Related Documentation

- PostHog Python SDK: https://posthog.com/docs/libraries/python
- Azure OpenAI API: https://learn.microsoft.com/en-us/azure/ai-services/openai/
- OpenAI Pricing: https://openai.com/api/pricing/
- Issue #21: Feature: Add PostHog LLM Analytics Instrumentation for Chat Endpoint
