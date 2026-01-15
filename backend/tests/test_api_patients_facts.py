"""Tests for patient facts API endpoint."""

import pytest

from app.api.patients import router


class TestPatientFactsEndpoint:
    """Tests for the GET /patients/{patient_id}/facts endpoint."""

    def test_facts_route_exists(self) -> None:
        """The facts endpoint should be registered."""
        route_paths = [route.path for route in router.routes]
        assert "/patients/{patient_id}/facts" in route_paths

    def test_facts_route_methods(self) -> None:
        """The facts endpoint should accept GET requests."""
        for route in router.routes:
            if route.path == "/patients/{patient_id}/facts":
                assert "GET" in route.methods
                break
        else:
            pytest.fail("Facts route not found")

    def test_facts_route_has_query_params(self) -> None:
        """The facts endpoint should accept query parameters for filtering."""
        for route in router.routes:
            if route.path == "/patients/{patient_id}/facts":
                # Get the function from the endpoint
                endpoint_func = route.endpoint
                import inspect

                sig = inspect.signature(endpoint_func)
                param_names = list(sig.parameters.keys())
                assert "patient_id" in param_names
                assert "domain" in param_names
                assert "assertion" in param_names
                assert "limit" in param_names
                assert "offset" in param_names
                break
        else:
            pytest.fail("Facts route not found")
