"""Tests for database configuration and base model."""

from uuid import UUID

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.core.database import Base


class SampleModel(Base):
    """Sample model for testing base class functionality."""

    __tablename__ = "sample_models"

    name: Mapped[str] = mapped_column(String(100), nullable=False)


class TestSettings:
    """Test application settings."""

    def test_database_url_configured(self) -> None:
        """Test that database URL is configured."""
        assert settings.database_url is not None
        assert "postgresql" in settings.database_url

    def test_sync_database_url(self) -> None:
        """Test sync database URL removes asyncpg."""
        sync_url = settings.sync_database_url
        assert "+asyncpg" not in sync_url
        assert "postgresql://" in sync_url or "postgresql+psycopg" in sync_url

    def test_redis_url_configured(self) -> None:
        """Test that Redis URL is configured."""
        assert settings.redis_url is not None
        assert "redis://" in settings.redis_url


class TestBaseModel:
    """Test Base model class."""

    def test_base_has_id_column(self) -> None:
        """Test that Base provides id column."""
        assert "id" in Base.__table__.c._all_columns if hasattr(Base, "__table__") else True
        # Check via the sample model
        assert "id" in SampleModel.__table__.c

    def test_base_has_created_at_column(self) -> None:
        """Test that Base provides created_at column."""
        assert "created_at" in SampleModel.__table__.c

    def test_sample_model_inherits_base(self) -> None:
        """Test that sample model inherits from Base."""
        assert issubclass(SampleModel, Base)

    def test_id_is_uuid_type(self) -> None:
        """Test that id column is UUID type."""
        id_col = SampleModel.__table__.c.id
        # Check that it's a UUID column
        assert "UUID" in str(id_col.type) or "uuid" in str(id_col.type).lower()

    def test_created_at_is_datetime_type(self) -> None:
        """Test that created_at column is DateTime type."""
        created_at_col = SampleModel.__table__.c.created_at
        assert "DateTime" in str(type(created_at_col.type).__name__)


class TestModelCreation:
    """Test model instance creation."""

    def test_create_sample_model(self) -> None:
        """Test creating a model instance."""
        model = SampleModel(name="Test")
        assert model.name == "Test"

    def test_model_id_can_be_set(self) -> None:
        """Test that model id can be explicitly set."""
        test_id = "550e8400-e29b-41d4-a716-446655440000"
        model = SampleModel(id=test_id, name="Test")
        assert model.id == test_id
        # Should be a valid UUID string
        UUID(model.id)  # Will raise if not valid UUID

    def test_model_tablename(self) -> None:
        """Test model has correct table name."""
        assert SampleModel.__tablename__ == "sample_models"

    def test_id_column_has_default(self) -> None:
        """Test that id column has a default function."""
        id_col = SampleModel.__table__.c.id
        assert id_col.default is not None
