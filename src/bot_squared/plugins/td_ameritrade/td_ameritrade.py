import logging
import os
import time
from datetime import datetime, timedelta, timezone

from selenium import webdriver
from tda.auth import easy_client
from tda.client import Client


class TDAmeritrade:
    def __init__(self, api_key=None, rate_limit=None):
        self.logger = logging.getLogger(__name__)
        self.api_key = api_key or os.getenv("TD_API_KEY")
        self.rate_limit = rate_limit or float(os.getenv("TD_RATE_LIMIT", "0"))

        self.yearly_charts = {}
        self.last_api_call = time.time()
        self.current_trading_session = None

        self._authenticate()

    def __del__(self):
        # cleanup socket
        del self.tda_api

    async def get_yearly_chart(self, symbol, date=None):
        """
        Retrieve yearly chart data for a given symbol.

        :param symbol: The stock symbol to retrieve data for.
        :param date: Optional date to retrieve data for. Defaults to current date.
        :return: List of candle data or None if retrieval fails.
        """
        if date is None:
            date = datetime.now(timezone.utc)

        if symbol in self.yearly_charts:
            return self.yearly_charts[symbol]
        else:
            year_chart_data = self.tda_api.get_price_history(
                symbol=symbol,
                period_type=Client.PriceHistory.PeriodType.YEAR,
                period=Client.PriceHistory.Period.ONE_YEAR,
                frequency_type=Client.PriceHistory.FrequencyType.DAILY,
                frequency=Client.PriceHistory.Frequency.DAILY,
                end_datetime=date,
            ).json()
            self.yearly_charts[symbol] = year_chart_data["candles"]
            return year_chart_data["candles"]

    async def get_quote(self, symbol):
        """
        Retrieve quote data for a given symbol.

        :param symbol: The stock symbol to retrieve data for.
        :return: Quote data or None if retrieval fails.
        """
        quote_data = self.tda_api.get_quote(symbol).json()
        return quote_data[symbol]

    async def is_market_open(self):
        """
        Check if the market is currently open.

        :return: True if the market is open, False otherwise.
        """
        market = self.tda_api.get_hours_for_single_market(Client.Markets.EQUITY, datetime.now(timezone.utc)).json()
        is_open = False
        variable_key = "EQ"
        if "EQ" in market["equity"]:
            variable_key = "EQ"
        elif "equity" in market["equity"]:
            variable_key = "equity"
        else:
            self.logger.error(f"Error isMarketOpen() - KeyError - {market} - Retrying...")
            return False
        is_open = market["equity"][variable_key]["isOpen"]
        if is_open:
            now = datetime.now(timezone(-timedelta(hours=5)))
            regular_market_open = datetime.strptime(
                market["equity"][variable_key]["sessionHours"]["regularMarket"][0]["start"],
                "%Y-%m-%dT%H:%M:%S%z",
            )
            regular_market_close = datetime.strptime(
                market["equity"][variable_key]["sessionHours"]["regularMarket"][0]["end"], "%Y-%m-%dT%H:%M:%S%z"
            )

            return (now > regular_market_open) and (now < regular_market_close)
        else:
            return False

    async def get_time_until_market_open(self):
        """
        Calculate the time until the market opens.

        :return: Time until market opens or None if retrieval fails.
        """
        now = datetime.now(timezone(-timedelta(hours=5)))

        if self.current_trading_session is not None:
            session = datetime.strptime(self.current_trading_session["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)

            # this is the current session still
            # it has to be either now or in the future, otherwise get a new session
            if session.day >= now.day and session.month >= now.month and session.year >= now.year:
                regular_market_open = datetime.strptime(
                    self.current_trading_session["sessionHours"]["regularMarket"][0]["start"], "%Y-%m-%dT%H:%M:%S%z"
                )
                return regular_market_open - now

        is_open = False
        date = datetime.now(timezone.utc)
        while not is_open:
            market = self.tda_api.get_hours_for_single_market(Client.Markets.EQUITY, date).json()
            variable_key = "EQ"
            if "EQ" in market["equity"]:
                variable_key = "EQ"
            elif "equity" in market["equity"]:
                variable_key = "equity"
            else:
                self.logger.error(f"Error isMarketOpen() - KeyError - {market} - Retrying...")
                continue
            is_open = market["equity"][variable_key]["isOpen"]
            if is_open:
                now = datetime.now(timezone(-timedelta(hours=5)))
                self.current_trading_session = market["equity"][variable_key]
                regular_market_open = datetime.strptime(
                    market["equity"][variable_key]["sessionHours"]["regularMarket"][0]["start"],
                    "%Y-%m-%dT%H:%M:%S%z",
                )
                return regular_market_open - now
            else:
                date = date + timedelta(days=1)

    async def get_time_until_market_close(self):
        """
        Calculate the time until the market closes.

        :return: Time until market closes or None if retrieval fails.
        """
        now = datetime.now(timezone(-timedelta(hours=5)))

        if self.current_trading_session is not None:
            session = datetime.strptime(self.current_trading_session["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)

            # this is the same day
            if session.day == now.day and session.month == now.month and session.year == now.year:
                return session["sessionHours"]["regularMarket"][0]["end"]

        else:  # No saved session data, call api
            market = self.tda_api.get_hours_for_single_market(Client.Markets.EQUITY, datetime.now(timezone.utc)).json()
            variable_key = "EQ"
            if "EQ" in market["equity"]:
                variable_key = "EQ"
            elif "equity" in market["equity"]:
                variable_key = "equity"
            else:
                self.logger.error("Error isMarketOpen() - KeyError - {market} - Retrying...")
                return None
            is_open = market["equity"][variable_key]["isOpen"]
            now = datetime.now(timezone(-timedelta(hours=5)))
            if is_open:
                self.current_trading_session = market["equity"][variable_key]
                regular_market_close = datetime.strptime(
                    market["equity"][variable_key]["sessionHours"]["regularMarket"][0]["end"],
                    "%Y-%m-%dT%H:%M:%S%z",
                )
                return regular_market_close - now
            else:
                return now - now

    def _authenticate(self):
        """
        Authenticate with the TD Ameritrade API.
        """
        self.tda_api = easy_client(
            api_key=self.api_key, redirect_uri="http://127.0.0.1", token_path=".token", webdriver_func=webdriver.Chrome
        )

    def _rate_limit(self):
        """
        Calculate the rate limit delay.

        :return: Time to wait before the next API call.
        """
        if time.time() - self.last_api_call < self.rate_limit:
            return self.rate_limit - (time.time() - self.last_api_call)
        else:
            return 0
