# tests/test_providers.py
"""
Provider Tests - Unit Tests for API Provider Classes

This module contains comprehensive unit tests for all provider classes,
including BRSAPIProvider, FastForexProvider, NavasanProvider, and WallexProvider.
It tests API interactions, caching behavior, error handling, and data processing functionality.

Files that USE this module:
- pytest (test runner executes these tests)

Files that this module USES:
- xrate.adapters.providers.brsapi (BRSAPIProvider for testing)
- xrate.adapters.providers.fastforex (FastForexProvider for testing)
- xrate.adapters.providers.navasan (NavasanProvider for testing)
- xrate.adapters.providers.wallex (WallexProvider for testing)
- unittest.mock (Mock for API mocking)
- pytest (testing framework)
"""
import pytest  # Testing framework for writing and running tests

from unittest.mock import Mock, patch  # Mock objects and patching for testing without real API calls
import requests  # HTTP library (used for mocking responses)
from datetime import datetime, timezone, timedelta  # Date/time utilities for testing cache timestamps

from xrate.adapters.providers.brsapi import BRSAPIProvider  # BRS API provider to test
from xrate.adapters.providers.fastforex import FastForexProvider  # FastForex API provider to test
from xrate.adapters.providers.navasan import NavasanProvider  # Navasan API provider to test
from xrate.adapters.providers.wallex import WallexProvider  # Wallex API provider to test


class TestFastForexProvider:
    def test_init_with_defaults(self):
        provider = FastForexProvider()
        assert provider.timeout == 10  # default from config
        assert "fastforex.io" in provider.url
        assert provider.ttl.total_seconds() == 15 * 60  # 15 minutes

    def test_init_with_custom_params(self):
        provider = FastForexProvider(base_url="http://test.com", timeout=5)
        assert provider.url == "http://test.com"
        assert provider.timeout == 5

    def test_cache_valid_with_no_cache(self):
        provider = FastForexProvider()
        assert not provider._cache_valid()

    @patch('xrate.adapters.providers.fastforex.datetime')
    def test_cache_valid_with_valid_cache(self, mock_datetime):
        provider = FastForexProvider()
        provider._cache_rate = 1.2
        provider._cache_ts = Mock()
        
        # Mock current time to be within TTL
        mock_now = Mock()
        mock_now.__sub__ = Mock(return_value=Mock(total_seconds=Mock(return_value=600)))  # 10 minutes
        mock_datetime.now.return_value = mock_now
        
        assert provider._cache_valid()

    @patch('xrate.adapters.providers.fastforex.requests.get')
    def test_eur_usd_rate_success(self, mock_get):
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "base": "USD",
            "results": {"EUR": 0.85}
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        provider = FastForexProvider()
        rate = provider.eur_usd_rate()
        
        # Should invert: 1 / 0.85 = 1.176...
        assert abs(rate - 1.176) < 0.01
        mock_get.assert_called_once()

    @patch('xrate.adapters.providers.fastforex.requests.get')
    def test_eur_usd_rate_api_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        
        provider = FastForexProvider()
        with pytest.raises(RuntimeError, match="FastForex API request failed"):
            provider.eur_usd_rate()

    @patch('xrate.adapters.providers.fastforex.requests.get')
    def test_eur_usd_rate_timeout(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout()
        
        provider = FastForexProvider()
        with pytest.raises(RuntimeError, match="FastForex API timeout"):
            provider.eur_usd_rate()

    @patch('xrate.adapters.providers.fastforex.requests.get')
    def test_eur_usd_rate_invalid_response(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"invalid": "structure"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        provider = FastForexProvider()
        with pytest.raises(RuntimeError, match="FastForex response missing"):
            provider.eur_usd_rate()

    @patch('xrate.adapters.providers.fastforex.requests.get')
    def test_eur_usd_rate_negative_value(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "base": "USD",
            "results": {"EUR": -0.85}  # Negative value
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        provider = FastForexProvider()
        with pytest.raises(RuntimeError, match="FastForex returned non-positive"):
            provider.eur_usd_rate()


class TestNavasanProvider:
    def test_init_with_defaults(self):
        provider = NavasanProvider()
        assert provider.timeout == 10
        assert "navasan.tech" in provider.url
        assert provider.ttl.total_seconds() == 28 * 60  # 28 minutes

    def test_init_without_api_key(self):
        with patch('providers.navasan.settings') as mock_settings:
            mock_settings.NAVASAN_URL = "http://test.com"
            with pytest.raises(ValueError, match="api_key not configured"):
                NavasanProvider()

    def test_extract_value_from_dict(self):
        # Test with dict containing 'value'
        result = NavasanProvider._extract_value({"value": "123", "change": 5})
        assert result == "123"

        # Test with dict without 'value'
        result = NavasanProvider._extract_value({"change": 5})
        assert result == '{"change": 5}'

        # Test with primitive types
        assert NavasanProvider._extract_value(123) == "123"
        assert NavasanProvider._extract_value("test") == "test"
        assert NavasanProvider._extract_value(None) is None

    @patch('xrate.adapters.providers.navasan.requests.get')
    def test_get_latest_raw_success(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"usd": {"value": "108400"}, "eur": {"value": "126000"}}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        provider = NavasanProvider()
        data = provider.get_latest_raw()
        
        assert data == {"usd": {"value": "108400"}, "eur": {"value": "126000"}}
        mock_get.assert_called_once()

    @patch('xrate.adapters.providers.navasan.requests.get')
    def test_get_latest_raw_api_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        
        provider = NavasanProvider()
        with pytest.raises(RuntimeError, match="Navasan API request failed"):
            provider.get_latest_raw()

    @patch('xrate.adapters.providers.navasan.requests.get')
    def test_get_latest_raw_invalid_json(self, mock_get):
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        provider = NavasanProvider()
        with pytest.raises(RuntimeError, match="Navasan API returned invalid JSON"):
            provider.get_latest_raw()

    @patch('xrate.adapters.providers.navasan.requests.get')
    def test_get_latest_raw_non_dict_response(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = "not a dict"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        provider = NavasanProvider()
        with pytest.raises(RuntimeError, match="Navasan returned non-dict JSON"):
            provider.get_latest_raw()

    @patch.object(NavasanProvider, 'get_latest_raw')
    def test_get_values(self, mock_get_raw):
        mock_get_raw.return_value = {
            "usd": {"value": "108400"},
            "eur": {"value": "126000"},
            "missing_key": None
        }

        provider = NavasanProvider()
        result = provider.get_values(["usd", "eur", "missing_key", "nonexistent"])
        
        expected = {
            "usd": "108400",
            "eur": "126000", 
            "missing_key": "NOT_FOUND",
            "nonexistent": "NOT_FOUND"
        }
        assert result == expected


class TestBRSAPIProvider:
    def test_init_with_defaults(self):
        provider = BRSAPIProvider()
        assert "brsapi.ir" in provider.url
        assert provider.timeout == 10  # default from config
        assert provider.ttl.total_seconds() == 15 * 60  # 15 minutes

    def test_init_with_custom_params(self):
        provider = BRSAPIProvider(base_url="http://test.com?key=test123", timeout=5)
        assert provider.url == "http://test.com?key=test123"
        assert provider.timeout == 5

    def test_init_without_key(self):
        with pytest.raises(ValueError, match="BRSAPI_URL contains empty or missing key"):
            BRSAPIProvider(base_url="http://test.com")

    def test_cache_valid_with_no_cache(self):
        provider = BRSAPIProvider(base_url="http://test.com?key=test123")
        assert not provider._cache_valid()

    @patch('xrate.adapters.providers.brsapi.datetime')
    def test_cache_valid_with_valid_cache(self, mock_datetime):
        provider = BRSAPIProvider(base_url="http://test.com?key=test123")
        BRSAPIProvider._cache_data = {"test": "data"}
        BRSAPIProvider._cache_ts = datetime.now(timezone.utc)
        
        # Mock current time to be within TTL
        mock_now = datetime.now(timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        assert provider._cache_valid()

    @patch('xrate.adapters.providers.brsapi.requests.get')
    def test_get_latest_raw_success(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "gold": [{"symbol": "IR_GOLD_18K", "price": "5000000"}],
            "currency": [
                {"symbol": "USD", "price": "108000"},
                {"symbol": "EUR", "price": "126000"}
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        provider = BRSAPIProvider(base_url="http://test.com?key=test123")
        data = provider.get_latest_raw()
        
        assert "gold" in data
        assert "currency" in data
        mock_get.assert_called_once()

    @patch('xrate.adapters.providers.brsapi.requests.get')
    def test_get_latest_raw_list_response(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = [{
            "gold": [{"symbol": "IR_GOLD_18K", "price": "5000000"}],
            "currency": [{"symbol": "USD", "price": "108000"}]
        }]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        provider = BRSAPIProvider(base_url="http://test.com?key=test123")
        data = provider.get_latest_raw()
        
        assert isinstance(data, dict)
        assert "gold" in data

    @patch('xrate.adapters.providers.brsapi.requests.get')
    def test_get_usd_toman(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "currency": [{"symbol": "USD", "price": "108000"}]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        provider = BRSAPIProvider(base_url="http://test.com?key=test123")
        usd = provider.get_usd_toman()
        
        assert usd == 108000

    @patch('xrate.adapters.providers.brsapi.requests.get')
    def test_get_eur_toman(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "currency": [{"symbol": "EUR", "price": "126000"}]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        provider = BRSAPIProvider(base_url="http://test.com?key=test123")
        eur = provider.get_eur_toman()
        
        assert eur == 126000

    @patch('xrate.adapters.providers.brsapi.requests.get')
    def test_get_gold_18k_toman(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "gold": [{"symbol": "IR_GOLD_18K", "price": "5000000"}]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        provider = BRSAPIProvider(base_url="http://test.com?key=test123")
        gold = provider.get_gold_18k_toman()
        
        assert gold == 5000000

    @patch('xrate.adapters.providers.brsapi.requests.get')
    def test_eur_usd_rate(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "currency": [
                {"symbol": "USD", "price": "108000"},
                {"symbol": "EUR", "price": "126000"}
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        provider = BRSAPIProvider(base_url="http://test.com?key=test123")
        rate = provider.eur_usd_rate()
        
        # EUR/USD = 126000 / 108000 = 1.1666...
        assert abs(rate - 1.1666) < 0.01

    @patch('xrate.adapters.providers.brsapi.requests.get')
    def test_eur_usd_rate_api_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        
        provider = BRSAPIProvider(base_url="http://test.com?key=test123")
        with pytest.raises(RuntimeError, match="BRS API request failed"):
            provider.eur_usd_rate()

    @patch('xrate.adapters.providers.brsapi.requests.get')
    def test_get_latest_raw_missing_fields(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"invalid": "structure"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        provider = BRSAPIProvider(base_url="http://test.com?key=test123")
        with pytest.raises(RuntimeError, match="BRS API response missing required fields"):
            provider.get_latest_raw()


class TestWallexProvider:
    def test_init_with_defaults(self):
        provider = WallexProvider()
        assert provider.url == "https://api.wallex.ir/v1/markets"
        assert provider.timeout == 10  # default from config
        assert provider.ttl.total_seconds() == 15 * 60  # 15 minutes

    def test_init_with_custom_params(self):
        provider = WallexProvider(base_url="http://test.com", timeout=5)
        assert provider.url == "http://test.com"
        assert provider.timeout == 5

    def test_cache_valid_with_no_cache(self):
        provider = WallexProvider()
        assert not provider._cache_valid()

    @patch('xrate.adapters.providers.wallex.datetime')
    def test_cache_valid_with_valid_cache(self, mock_datetime):
        provider = WallexProvider()
        WallexProvider._cache_data = {"test": "data"}
        WallexProvider._cache_ts = datetime.now(timezone.utc)
        
        mock_now = datetime.now(timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        assert provider._cache_valid()

    @patch('xrate.adapters.providers.wallex.requests.get')
    def test_get_latest_raw_success(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": {
                "symbols": {
                    "USDTTMN": {
                        "symbol": "USDTTMN",
                        "stats": {
                            "lastPrice": "108692.0000000000000000",
                            "24h_ch": -0.04
                        }
                    }
                }
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        provider = WallexProvider()
        data = provider.get_latest_raw()
        
        assert "result" in data
        assert "symbols" in data["result"]
        mock_get.assert_called_once()

    @patch('xrate.adapters.providers.wallex.requests.get')
    def test_get_tether_data_success(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": {
                "symbols": {
                    "USDTTMN": {
                        "symbol": "USDTTMN",
                        "stats": {
                            "lastPrice": "108692.0000000000000000",
                            "24h_ch": -0.04
                        }
                    }
                }
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        provider = WallexProvider()
        tether_data = provider.get_tether_data()
        
        assert tether_data is not None
        assert "price" in tether_data
        assert "24h_ch" in tether_data
        assert tether_data["price"] == 108692.0
        assert tether_data["24h_ch"] == -0.04

    @patch('xrate.adapters.providers.wallex.requests.get')
    def test_get_tether_data_missing_symbol(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": {
                "symbols": {}
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        provider = WallexProvider()
        tether_data = provider.get_tether_data()
        
        assert tether_data is None

    @patch('xrate.adapters.providers.wallex.requests.get')
    def test_get_tether_price_toman(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": {
                "symbols": {
                    "USDTTMN": {
                        "stats": {
                            "lastPrice": "108692.0000000000000000",
                            "24h_ch": -0.04
                        }
                    }
                }
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        provider = WallexProvider()
        price = provider.get_tether_price_toman()
        
        assert price == 108692

    @patch('xrate.adapters.providers.wallex.requests.get')
    def test_get_tether_24h_change(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": {
                "symbols": {
                    "USDTTMN": {
                        "stats": {
                            "lastPrice": "108692.0000000000000000",
                            "24h_ch": -0.04
                        }
                    }
                }
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        provider = WallexProvider()
        change = provider.get_tether_24h_change()
        
        assert change == -0.04

    @patch('xrate.adapters.providers.wallex.requests.get')
    def test_get_latest_raw_api_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        
        provider = WallexProvider()
        with pytest.raises(RuntimeError, match="Wallex API request failed"):
            provider.get_latest_raw()

    @patch('xrate.adapters.providers.wallex.requests.get')
    def test_get_latest_raw_timeout(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout()
        
        provider = WallexProvider()
        with pytest.raises(RuntimeError, match="Wallex API timeout"):
            provider.get_latest_raw()

    @patch('xrate.adapters.providers.wallex.requests.get')
    def test_get_latest_raw_missing_result(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"invalid": "structure"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        provider = WallexProvider()
        with pytest.raises(RuntimeError, match="Wallex API response missing"):
            provider.get_latest_raw()
