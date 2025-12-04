# tests/test_rates_service.py
"""
Rates Service Tests - Unit Tests for Business Logic Services

This module contains unit tests for the rates service layer, including
RatesService class, utility functions, and IRR snapshot functionality.
It tests business logic, data processing, and service integration.

Files that USE this module:
- pytest (test runner executes these tests)

Files that this module USES:
- xrate.application.rates_service (RatesService, get_irr_snapshot, utility functions)
- xrate.domain.models (IrrSnapshot for test data)
- unittest.mock (Mock for service mocking)
- pytest (testing framework)
"""
import pytest  # Testing framework for writing and running tests

from unittest.mock import Mock, patch  # Mock objects and patching for testing without real dependencies

from xrate.application.rates_service import RatesService, get_irr_snapshot, _to_int  # Service classes and functions to test
from xrate.domain.models import IrrSnapshot  # Domain model for test data


class TestRatesService:
    def test_init(self):
        mock_provider = Mock()
        service = RatesService(provider=mock_provider)
        assert service.provider == mock_provider

    def test_eur_usd(self):
        mock_provider = Mock()
        mock_provider.eur_usd_rate.return_value = 1.1234
        
        service = RatesService(provider=mock_provider)
        result = service.eur_usd()
        
        assert result == 1.1234
        mock_provider.eur_usd_rate.assert_called_once()


class TestUtilityFunctions:
    def test_to_int_with_commas(self):
        assert _to_int("10,948,570") == 10948570
        assert _to_int("1,234") == 1234

    def test_to_int_without_commas(self):
        assert _to_int("108400") == 108400
        assert _to_int("123") == 123

    def test_to_int_with_decimals(self):
        assert _to_int("123.45") == 123
        assert _to_int("108400.99") == 108400

    def test_to_int_with_none_or_empty(self):
        assert _to_int(None) == 0
        assert _to_int("") == 0
        assert _to_int(0) == 0


class TestIrrSnapshot:
    def test_creation(self):
        snapshot = IrrSnapshot(
            usd_toman=108400,
            eur_toman=126000,
            gold_1g_toman=10812360
        )
        assert snapshot.usd_toman == 108400
        assert snapshot.eur_toman == 126000
        assert snapshot.gold_1g_toman == 10812360


class TestGetIrrSnapshot:
    @patch('xrate.application.rates_service.NavasanProvider')
    def test_get_irr_snapshot_success(self, mock_navasan_class):
        # Mock the provider instance
        mock_provider = Mock()
        mock_provider.get_values.return_value = {
            "usd": "108400",
            "eur": "126000", 
            "18ayar": "10812360"
        }
        mock_navasan_class.return_value = mock_provider

        result = get_irr_snapshot()
        
        assert isinstance(result, IrrSnapshot)
        assert result.usd_toman == 108400
        assert result.eur_toman == 126000
        assert result.gold_1g_toman == 10812360

    @patch('xrate.application.rates_service.NavasanProvider')
    def test_get_irr_snapshot_with_missing_values(self, mock_navasan_class):
        # Mock the provider instance
        mock_provider = Mock()
        mock_provider.get_values.return_value = {
            "usd": "NOT_FOUND",
            "eur": "126000",
            "18ayar": "10812360"
        }
        mock_navasan_class.return_value = mock_provider

        result = get_irr_snapshot()
        
        # Should return None if any value is NOT_FOUND
        assert result is None

    @patch('xrate.application.rates_service.NavasanProvider')
    def test_get_irr_snapshot_with_exception(self, mock_navasan_class):
        # Mock provider to raise exception
        mock_navasan_class.side_effect = Exception("Navasan Error")
        
        # Should return None when all providers fail (exception is caught)
        result = get_irr_snapshot()
        assert result is None
