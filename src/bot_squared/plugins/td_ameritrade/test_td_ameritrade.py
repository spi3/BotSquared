from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from bot_squared.plugins.td_ameritrade.td_ameritrade import TDAmeritrade


@pytest.fixture
def tdameritrade():
    with patch.object(TDAmeritrade, "_authenticate"):
        td = TDAmeritrade(api_key="fake", rate_limit=0)
        td.tda_api = MagicMock()
        return td


def test_get_yearly_chart_cached(tdameritrade):
    tdameritrade.yearly_charts["AAPL"] = [{"close": 100}]
    result = tdameritrade.get_yearly_chart("AAPL")
    assert result == [{"close": 100}]


@patch("bot_squared.plugins.td_ameritrade.td_ameritrade.Client")
def test_get_yearly_chart_api(mock_client, tdameritrade):
    mock_api = tdameritrade.tda_api
    mock_api.get_price_history.return_value.json.return_value = {"candles": [{"close": 200}]}
    result = tdameritrade.get_yearly_chart("GOOG")
    assert result == [{"close": 200}]
    assert tdameritrade.yearly_charts["GOOG"] == [{"close": 200}]


def test_get_quote(tdameritrade):
    tdameritrade.tda_api.get_quote.return_value.json.return_value = {"AAPL": {"price": 150}}
    result = tdameritrade.get_quote("AAPL")
    assert result == {"price": 150}


def test_is_market_open_true(tdameritrade):
    tdameritrade.tda_api.get_hours_for_single_market.return_value.json.return_value = {
        "equity": {
            "EQ": {
                "isOpen": True,
                "sessionHours": {
                    "regularMarket": [{"start": "2023-01-01T14:30:00+0000", "end": "2023-01-01T21:00:00+0000"}]
                },
                "date": "2023-01-01",
            }
        }
    }
    with patch("bot_squared.plugins.td_ameritrade.td_ameritrade.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2023, 1, 1, 15, 0, tzinfo=timezone.utc)
        mock_datetime.strptime.side_effect = lambda *a, **k: datetime.strptime(*a, **k).replace(tzinfo=timezone.utc)
        result = tdameritrade.is_market_open()
        assert result is True


def test_is_market_open_false(tdameritrade):
    tdameritrade.tda_api.get_hours_for_single_market.return_value.json.return_value = {
        "equity": {
            "EQ": {
                "isOpen": False,
                "sessionHours": {
                    "regularMarket": [{"start": "2023-01-01T14:30:00+0000", "end": "2023-01-01T21:00:00+0000"}]
                },
                "date": "2023-01-01",
            }
        }
    }
    result = tdameritrade.is_market_open()
    assert result is False
