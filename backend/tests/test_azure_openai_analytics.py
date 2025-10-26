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
