"""Tests for Redis queue configuration."""

from unittest.mock import MagicMock, patch

import pytest

# Skip all tests if rq is not installed
rq = pytest.importorskip("rq", reason="rq package required for queue tests")


class TestQueueModule:
    """Test queue module imports and functions."""

    def test_queue_module_importable(self) -> None:
        """Test that queue module can be imported."""
        from app.core import queue

        assert queue is not None

    def test_queue_has_get_queue(self) -> None:
        """Test queue module has get_queue function."""
        from app.core.queue import get_queue

        assert callable(get_queue)

    def test_queue_has_enqueue_job(self) -> None:
        """Test queue module has enqueue_job function."""
        from app.core.queue import enqueue_job

        assert callable(enqueue_job)

    def test_queue_has_get_job(self) -> None:
        """Test queue module has get_job function."""
        from app.core.queue import get_job

        assert callable(get_job)

    def test_queue_has_get_job_status(self) -> None:
        """Test queue module has get_job_status function."""
        from app.core.queue import get_job_status

        assert callable(get_job_status)

    def test_queue_names_defined(self) -> None:
        """Test that queue names are defined."""
        from app.core.queue import QUEUE_NAMES

        assert "document" in QUEUE_NAMES
        assert "nlp" in QUEUE_NAMES
        assert "mapping" in QUEUE_NAMES
        assert "graph" in QUEUE_NAMES
        assert "export" in QUEUE_NAMES

    def test_queue_has_clear_queues(self) -> None:
        """Test queue module has clear_queues function."""
        from app.core.queue import clear_queues

        assert callable(clear_queues)

    def test_queue_has_get_document_queue(self) -> None:
        """Test queue module has get_document_queue function."""
        from app.core.queue import get_document_queue

        assert callable(get_document_queue)


class TestGetQueue:
    """Test get_queue function."""

    @patch("app.core.queue.get_redis")
    @patch("app.core.queue.Queue")
    def test_get_queue_creates_queue_with_connection(
        self, mock_queue_class: MagicMock, mock_redis: MagicMock
    ) -> None:
        """Test that get_queue creates Queue with Redis connection."""
        from app.core.queue import _queues, get_queue

        # Clear cache
        _queues.clear()

        mock_redis_conn = MagicMock()
        mock_redis.return_value = mock_redis_conn

        get_queue()

        mock_queue_class.assert_called_once()
        call_kwargs = mock_queue_class.call_args[1]
        assert call_kwargs["connection"] == mock_redis_conn

        # Clean up
        _queues.clear()

    @patch("app.core.queue.get_redis")
    @patch("app.core.queue.Queue")
    def test_get_queue_uses_default_name(
        self, mock_queue_class: MagicMock, mock_redis: MagicMock
    ) -> None:
        """Test that get_queue uses 'default' name by default."""
        from app.core.queue import _queues, get_queue

        # Clear cache
        _queues.clear()

        mock_redis.return_value = MagicMock()

        get_queue()

        call_kwargs = mock_queue_class.call_args[1]
        assert call_kwargs["name"] == "default"

        # Clean up
        _queues.clear()

    @patch("app.core.queue.get_redis")
    @patch("app.core.queue.Queue")
    def test_get_queue_uses_custom_name(
        self, mock_queue_class: MagicMock, mock_redis: MagicMock
    ) -> None:
        """Test that get_queue can use custom queue name."""
        from app.core.queue import _queues, get_queue

        # Clear cache
        _queues.clear()

        mock_redis.return_value = MagicMock()

        get_queue("my_custom_queue")

        call_kwargs = mock_queue_class.call_args[1]
        assert call_kwargs["name"] == "my_custom_queue"

        # Clean up
        _queues.clear()

    @patch("app.core.queue.get_redis")
    @patch("app.core.queue.Queue")
    def test_get_queue_caches_queues(
        self, mock_queue_class: MagicMock, mock_redis: MagicMock
    ) -> None:
        """Test that get_queue caches queue instances."""
        from app.core.queue import _queues, get_queue

        # Clear cache
        _queues.clear()

        mock_redis.return_value = MagicMock()
        mock_queue_class.return_value = MagicMock()

        # Call twice with same name
        q1 = get_queue("test")
        q2 = get_queue("test")

        # Should only create one queue
        assert mock_queue_class.call_count == 1
        assert q1 is q2

        # Clean up
        _queues.clear()


class TestEnqueueJob:
    """Test enqueue_job function."""

    @patch("app.core.queue.get_queue")
    def test_enqueue_job_calls_queue_enqueue(
        self, mock_get_queue: MagicMock
    ) -> None:
        """Test that enqueue_job calls queue.enqueue."""
        from app.core.queue import enqueue_job

        mock_queue = MagicMock()
        mock_get_queue.return_value = mock_queue

        def sample_job(x: int) -> int:
            return x * 2

        enqueue_job(sample_job, 5)

        mock_queue.enqueue.assert_called_once()

    @patch("app.core.queue.get_queue")
    def test_enqueue_job_uses_default_queue(
        self, mock_get_queue: MagicMock
    ) -> None:
        """Test that enqueue_job uses default queue."""
        from app.core.queue import enqueue_job

        mock_queue = MagicMock()
        mock_get_queue.return_value = mock_queue

        enqueue_job(lambda: None)

        mock_get_queue.assert_called_with("default")

    @patch("app.core.queue.get_queue")
    def test_enqueue_job_uses_custom_queue(
        self, mock_get_queue: MagicMock
    ) -> None:
        """Test that enqueue_job can use custom queue."""
        from app.core.queue import enqueue_job

        mock_queue = MagicMock()
        mock_get_queue.return_value = mock_queue

        enqueue_job(lambda: None, queue_name="my_queue")

        mock_get_queue.assert_called_with("my_queue")

    @patch("app.core.queue.get_queue")
    def test_enqueue_job_passes_timeout(
        self, mock_get_queue: MagicMock
    ) -> None:
        """Test that enqueue_job passes job_timeout."""
        from app.core.queue import enqueue_job

        mock_queue = MagicMock()
        mock_get_queue.return_value = mock_queue

        enqueue_job(lambda: None, job_timeout=300)

        call_kwargs = mock_queue.enqueue.call_args[1]
        assert call_kwargs["job_timeout"] == 300

    @patch("app.core.queue.get_queue")
    def test_enqueue_job_passes_job_id(
        self, mock_get_queue: MagicMock
    ) -> None:
        """Test that enqueue_job can pass custom job_id."""
        from uuid import uuid4

        from app.core.queue import enqueue_job

        mock_queue = MagicMock()
        mock_get_queue.return_value = mock_queue

        custom_id = uuid4()
        enqueue_job(lambda: None, job_id=custom_id)

        call_kwargs = mock_queue.enqueue.call_args[1]
        assert call_kwargs["job_id"] == str(custom_id)


class TestGetJob:
    """Test get_job function."""

    @patch("app.core.queue.get_redis")
    @patch("app.core.queue.Job.fetch")
    def test_get_job_fetches_by_id(
        self, mock_fetch: MagicMock, mock_redis: MagicMock
    ) -> None:
        """Test that get_job fetches job by ID."""
        from app.core.queue import get_job

        mock_redis_conn = MagicMock()
        mock_redis.return_value = mock_redis_conn
        mock_job = MagicMock()
        mock_fetch.return_value = mock_job

        result = get_job("test-job-id")

        mock_fetch.assert_called_once_with("test-job-id", connection=mock_redis_conn)
        assert result == mock_job

    @patch("app.core.queue.get_redis")
    @patch("app.core.queue.Job.fetch")
    def test_get_job_returns_none_on_error(
        self, mock_fetch: MagicMock, mock_redis: MagicMock
    ) -> None:
        """Test that get_job returns None when job not found."""
        from app.core.queue import get_job

        mock_redis.return_value = MagicMock()
        mock_fetch.side_effect = Exception("Job not found")

        result = get_job("nonexistent-job-id")

        assert result is None

    @patch("app.core.queue.get_redis")
    @patch("app.core.queue.Job.fetch")
    def test_get_job_handles_uuid_id(
        self, mock_fetch: MagicMock, mock_redis: MagicMock
    ) -> None:
        """Test that get_job handles UUID job IDs."""
        from uuid import uuid4

        from app.core.queue import get_job

        mock_redis_conn = MagicMock()
        mock_redis.return_value = mock_redis_conn
        mock_job = MagicMock()
        mock_fetch.return_value = mock_job

        job_uuid = uuid4()
        result = get_job(job_uuid)

        mock_fetch.assert_called_once_with(str(job_uuid), connection=mock_redis_conn)
        assert result == mock_job


class TestGetJobStatus:
    """Test get_job_status function."""

    @patch("app.core.queue.get_job")
    def test_get_job_status_returns_status(
        self, mock_get_job: MagicMock
    ) -> None:
        """Test that get_job_status returns job status."""
        from app.core.queue import get_job_status

        mock_job = MagicMock()
        mock_job.get_status.return_value = "finished"
        mock_get_job.return_value = mock_job

        result = get_job_status("test-job-id")

        assert result == "finished"

    @patch("app.core.queue.get_job")
    def test_get_job_status_returns_none_when_not_found(
        self, mock_get_job: MagicMock
    ) -> None:
        """Test that get_job_status returns None when job not found."""
        from app.core.queue import get_job_status

        mock_get_job.return_value = None

        result = get_job_status("nonexistent-job-id")

        assert result is None


class TestGetJobResult:
    """Test get_job_result function."""

    @patch("app.core.queue.get_job")
    def test_get_job_result_returns_result(
        self, mock_get_job: MagicMock
    ) -> None:
        """Test that get_job_result returns job result."""
        from app.core.queue import get_job_result

        mock_job = MagicMock()
        mock_job.result = {"processed": True}
        mock_get_job.return_value = mock_job

        result = get_job_result("test-job-id")

        assert result == {"processed": True}

    @patch("app.core.queue.get_job")
    def test_get_job_result_returns_none_when_not_found(
        self, mock_get_job: MagicMock
    ) -> None:
        """Test that get_job_result returns None when job not found."""
        from app.core.queue import get_job_result

        mock_get_job.return_value = None

        result = get_job_result("nonexistent-job-id")

        assert result is None


class TestClearQueues:
    """Test clear_queues function."""

    @patch("app.core.queue.get_redis")
    @patch("app.core.queue.Queue")
    def test_clear_queues_empties_all_queues(
        self, mock_queue_class: MagicMock, mock_redis: MagicMock
    ) -> None:
        """Test that clear_queues empties all cached queues."""
        from app.core.queue import _queues, clear_queues, get_queue

        # Clear any existing cache
        _queues.clear()

        mock_redis.return_value = MagicMock()
        mock_queue1 = MagicMock()
        mock_queue2 = MagicMock()
        mock_queue_class.side_effect = [mock_queue1, mock_queue2]

        # Create some queues
        get_queue("queue1")
        get_queue("queue2")

        assert len(_queues) == 2

        # Clear them
        clear_queues()

        mock_queue1.empty.assert_called_once()
        mock_queue2.empty.assert_called_once()
        assert len(_queues) == 0

    def test_clear_queues_handles_empty_cache(self) -> None:
        """Test that clear_queues handles empty queue cache."""
        from app.core.queue import _queues, clear_queues

        _queues.clear()

        # Should not raise
        clear_queues()

        assert len(_queues) == 0


class TestSpecializedQueues:
    """Test specialized queue getter functions."""

    @patch("app.core.queue.get_queue")
    def test_get_document_queue(self, mock_get_queue: MagicMock) -> None:
        """Test get_document_queue uses correct queue name."""
        from app.core.queue import QUEUE_NAMES, get_document_queue

        mock_get_queue.return_value = MagicMock()

        get_document_queue()

        mock_get_queue.assert_called_with(QUEUE_NAMES["document"])

    @patch("app.core.queue.get_queue")
    def test_get_nlp_queue(self, mock_get_queue: MagicMock) -> None:
        """Test get_nlp_queue uses correct queue name."""
        from app.core.queue import QUEUE_NAMES, get_nlp_queue

        mock_get_queue.return_value = MagicMock()

        get_nlp_queue()

        mock_get_queue.assert_called_with(QUEUE_NAMES["nlp"])

    @patch("app.core.queue.get_queue")
    def test_get_mapping_queue(self, mock_get_queue: MagicMock) -> None:
        """Test get_mapping_queue uses correct queue name."""
        from app.core.queue import QUEUE_NAMES, get_mapping_queue

        mock_get_queue.return_value = MagicMock()

        get_mapping_queue()

        mock_get_queue.assert_called_with(QUEUE_NAMES["mapping"])

    @patch("app.core.queue.get_queue")
    def test_get_graph_queue(self, mock_get_queue: MagicMock) -> None:
        """Test get_graph_queue uses correct queue name."""
        from app.core.queue import QUEUE_NAMES, get_graph_queue

        mock_get_queue.return_value = MagicMock()

        get_graph_queue()

        mock_get_queue.assert_called_with(QUEUE_NAMES["graph"])

    @patch("app.core.queue.get_queue")
    def test_get_export_queue(self, mock_get_queue: MagicMock) -> None:
        """Test get_export_queue uses correct queue name."""
        from app.core.queue import QUEUE_NAMES, get_export_queue

        mock_get_queue.return_value = MagicMock()

        get_export_queue()

        mock_get_queue.assert_called_with(QUEUE_NAMES["export"])
