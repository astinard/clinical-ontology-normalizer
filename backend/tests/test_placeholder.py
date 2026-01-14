"""Placeholder test to verify pytest infrastructure works."""


def test_placeholder() -> None:
    """Placeholder test - will be replaced with real tests."""
    assert True, "Placeholder test should pass"


def test_version_exists() -> None:
    """Verify app version is defined."""
    from app import __version__

    assert __version__ == "0.1.0"
