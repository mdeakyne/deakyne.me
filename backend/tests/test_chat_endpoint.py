"""
Tests for the chat endpoint
"""
import pytest
from fastapi.testclient import TestClient
import json
import os
import sys
from unittest.mock import Mock, patch, AsyncMock

# Add backend directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app, generate_session_id, load_conversation_history, save_message


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_auth_token():
    """Mock authentication token"""
    return "test-bearer-token"


@pytest.fixture
def mock_session_id():
    """Mock session ID"""
    return "test-session-123"


class TestChatEndpointAuth:
    """Tests for chat endpoint authentication"""

    def test_chat_requires_auth(self, client):
        """Test that chat endpoint requires authentication"""
        response = client.post("/api/chat", json={"message": "Hello"})
        assert response.status_code == 401
        assert "Authorization header required" in response.json()["detail"]

    def test_chat_invalid_token(self, client):
        """Test chat with invalid token"""
        response = client.post(
            "/api/chat",
            headers={"Authorization": "Bearer invalid-token"},
            json={"message": "Hello"}
        )
        assert response.status_code == 401


class TestChatEndpointValidation:
    """Tests for chat endpoint input validation"""

    def test_chat_empty_message(self, client, mock_auth_token):
        """Test chat with empty message"""
        with patch("main.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "test@example.com"}

            response = client.post(
                "/api/chat",
                headers={"Authorization": f"Bearer {mock_auth_token}"},
                json={"message": ""}
            )
            assert response.status_code == 400
            assert "Message cannot be empty" in response.json()["detail"]

    def test_chat_message_too_long(self, client, mock_auth_token):
        """Test chat with message exceeding max length"""
        with patch("main.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "test@example.com"}

            long_message = "x" * 2001  # Exceeds 2000 char limit
            response = client.post(
                "/api/chat",
                headers={"Authorization": f"Bearer {mock_auth_token}"},
                json={"message": long_message}
            )
            assert response.status_code == 400
            assert "Message too long" in response.json()["detail"]


class TestChatEndpointRateLimiting:
    """Tests for chat endpoint rate limiting"""

    @patch("main.chat_rate_limiter")
    def test_chat_rate_limit_exceeded(self, mock_rate_limiter, client, mock_auth_token):
        """Test that rate limiting works"""
        with patch("main.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "test@example.com"}

            # Mock rate limiter to raise 429
            from fastapi import HTTPException
            mock_rate_limiter.check_rate_limit.side_effect = HTTPException(
                status_code=429,
                detail="Rate limit exceeded"
            )

            response = client.post(
                "/api/chat",
                headers={"Authorization": f"Bearer {mock_auth_token}"},
                json={"message": "Hello"}
            )
            assert response.status_code == 429


class TestChatEndpointFunctionality:
    """Tests for chat endpoint core functionality"""

    @patch("main.azure_client")
    @patch("main.chat_rate_limiter")
    @patch("main.ToolExecutor")
    def test_chat_basic_success(
        self,
        mock_tool_executor_class,
        mock_rate_limiter,
        mock_azure_client,
        client,
        mock_auth_token
    ):
        """Test successful chat completion"""
        with patch("main.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "test@example.com"}

            # Mock rate limiter to pass
            mock_rate_limiter.check_rate_limit.return_value = None

            # Mock Azure OpenAI response
            mock_azure_client.chat_completion = AsyncMock(
                return_value=("Matt is a technical educator based in Lawrence, Kansas.", 100)
            )

            response = client.post(
                "/api/chat",
                headers={"Authorization": f"Bearer {mock_auth_token}"},
                json={"message": "Who is Matt?"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            assert "session_id" in data
            assert "Matt" in data["response"]
            assert data["tokens_used"] == 100

    @patch("main.azure_client")
    @patch("main.chat_rate_limiter")
    @patch("main.ToolExecutor")
    def test_chat_with_session_id(
        self,
        mock_tool_executor_class,
        mock_rate_limiter,
        mock_azure_client,
        client,
        mock_auth_token,
        mock_session_id
    ):
        """Test chat with existing session ID"""
        with patch("main.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "test@example.com"}

            mock_rate_limiter.check_rate_limit.return_value = None
            mock_azure_client.chat_completion = AsyncMock(
                return_value=("Follow-up response", 50)
            )

            response = client.post(
                "/api/chat",
                headers={"Authorization": f"Bearer {mock_auth_token}"},
                json={
                    "message": "Tell me more",
                    "session_id": mock_session_id
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == mock_session_id

    @patch("main.azure_client")
    @patch("main.chat_rate_limiter")
    def test_chat_ai_error_handling(
        self,
        mock_rate_limiter,
        mock_azure_client,
        client,
        mock_auth_token
    ):
        """Test error handling when Azure OpenAI fails"""
        with patch("main.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "test@example.com"}

            mock_rate_limiter.check_rate_limit.return_value = None

            # Mock Azure OpenAI to raise an error
            mock_azure_client.chat_completion = AsyncMock(
                side_effect=Exception("API Error")
            )

            response = client.post(
                "/api/chat",
                headers={"Authorization": f"Bearer {mock_auth_token}"},
                json={"message": "Hello"}
            )

            assert response.status_code == 500
            assert "Failed to process chat request" in response.json()["detail"]


class TestHelperFunctions:
    """Tests for helper functions"""

    def test_generate_session_id(self):
        """Test session ID generation"""
        session_id = generate_session_id()
        assert isinstance(session_id, str)
        assert len(session_id) > 0
        # Should be a valid UUID format
        parts = session_id.split('-')
        assert len(parts) == 5

    def test_generate_unique_session_ids(self):
        """Test that session IDs are unique"""
        id1 = generate_session_id()
        id2 = generate_session_id()
        assert id1 != id2


class TestConversationHistory:
    """Tests for conversation history management"""

    @patch("main.get_db")
    def test_save_message(self, mock_get_db):
        """Test saving a message to database"""
        # Mock database
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = mock_conn

        save_message("test@example.com", "session-123", "user", "Hello")

        # Verify cursor was called with correct SQL
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert "INSERT INTO chat_conversations" in call_args[0][0]
        assert call_args[0][1] == ("test@example.com", "session-123", "user", "Hello")

    @patch("main.get_db")
    def test_load_conversation_history(self, mock_get_db):
        """Test loading conversation history"""
        # Mock database with some conversation history
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor

        # Mock fetchall to return conversation messages
        mock_cursor.fetchall.return_value = [
            {"message_role": "user", "message_content": "Hello"},
            {"message_role": "assistant", "message_content": "Hi there!"},
        ]
        mock_get_db.return_value.__enter__.return_value = mock_conn

        messages = load_conversation_history("test@example.com", "session-123")

        # Should return messages in chronological order (reversed from DB query)
        assert len(messages) == 2
        assert messages[0]["role"] == "assistant"  # Reversed order
        assert messages[0]["content"] == "Hi there!"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
