"""Tests for Redis connection module."""

from unittest.mock import MagicMock, patch

from app.core import redis as redis_module


class TestRedisConnection:
    """Test Redis connection management."""

    def setup_method(self) -> None:
        """Reset Redis client before each test."""
        redis_module._redis_client = None

    def teardown_method(self) -> None:
        """Clean up after each test."""
        redis_module._redis_client = None

    @patch("app.core.redis.Redis")
    def test_get_redis_creates_connection(self, mock_redis_class: MagicMock) -> None:
        """Test that get_redis creates a new connection on first call."""
        mock_client = MagicMock()
        mock_redis_class.from_url.return_value = mock_client

        result = redis_module.get_redis()

        assert result == mock_client
        mock_redis_class.from_url.assert_called_once()

    @patch("app.core.redis.Redis")
    def test_get_redis_reuses_connection(self, mock_redis_class: MagicMock) -> None:
        """Test that get_redis reuses existing connection."""
        mock_client = MagicMock()
        mock_redis_class.from_url.return_value = mock_client

        result1 = redis_module.get_redis()
        result2 = redis_module.get_redis()

        assert result1 == result2
        # Should only create one connection
        assert mock_redis_class.from_url.call_count == 1

    @patch("app.core.redis.Redis")
    def test_get_redis_uses_settings_url(self, mock_redis_class: MagicMock) -> None:
        """Test that get_redis uses URL from settings."""
        mock_client = MagicMock()
        mock_redis_class.from_url.return_value = mock_client

        redis_module.get_redis()

        # Verify from_url was called with decode_responses=True
        call_kwargs = mock_redis_class.from_url.call_args[1]
        assert call_kwargs.get("decode_responses") is True

    @patch("app.core.redis.Redis")
    def test_close_redis_closes_connection(self, mock_redis_class: MagicMock) -> None:
        """Test that close_redis closes the connection."""
        mock_client = MagicMock()
        mock_redis_class.from_url.return_value = mock_client

        # Create connection
        redis_module.get_redis()
        # Close it
        redis_module.close_redis()

        mock_client.close.assert_called_once()
        assert redis_module._redis_client is None

    def test_close_redis_handles_no_connection(self) -> None:
        """Test that close_redis handles case when no connection exists."""
        # Should not raise
        redis_module.close_redis()
        assert redis_module._redis_client is None

    @patch("app.core.redis.Redis")
    def test_close_redis_allows_new_connection(self, mock_redis_class: MagicMock) -> None:
        """Test that after close_redis, new connection can be created."""
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()
        mock_redis_class.from_url.side_effect = [mock_client1, mock_client2]

        # Create, close, create again
        redis_module.get_redis()
        redis_module.close_redis()
        result = redis_module.get_redis()

        assert result == mock_client2
        assert mock_redis_class.from_url.call_count == 2


class TestPingRedis:
    """Test Redis ping functionality."""

    def setup_method(self) -> None:
        """Reset Redis client before each test."""
        redis_module._redis_client = None

    def teardown_method(self) -> None:
        """Clean up after each test."""
        redis_module._redis_client = None

    @patch("app.core.redis.Redis")
    def test_ping_redis_returns_true_on_success(self, mock_redis_class: MagicMock) -> None:
        """Test ping_redis returns True when Redis responds."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis_class.from_url.return_value = mock_client

        result = redis_module.ping_redis()

        assert result is True
        mock_client.ping.assert_called_once()

    @patch("app.core.redis.Redis")
    def test_ping_redis_returns_false_on_failure(self, mock_redis_class: MagicMock) -> None:
        """Test ping_redis returns False when Redis fails."""
        mock_client = MagicMock()
        mock_client.ping.side_effect = Exception("Connection refused")
        mock_redis_class.from_url.return_value = mock_client

        result = redis_module.ping_redis()

        assert result is False

    @patch("app.core.redis.Redis")
    def test_ping_redis_returns_false_on_connection_error(
        self, mock_redis_class: MagicMock
    ) -> None:
        """Test ping_redis returns False when connection fails."""
        mock_redis_class.from_url.side_effect = Exception("Connection refused")

        result = redis_module.ping_redis()

        assert result is False
