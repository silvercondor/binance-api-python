import urllib.request
import urllib.parse
import json
import ssl
import datetime
import hmac
import hashlib
import time
from decimal import Decimal
from collections import namedtuple


# TODO: figure out how to make SSL work and get ride of this
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

__URL_BASE = "https://www.binance.com/api/"
__api_key = None
__api_secret_key = None
__log_enabled = False

# TODO: https://www.binance.com/exchange/public/product


def __timestamp():
    return int(round(time.time() * 1000))


def __v1_url(endpoint):
    return __URL_BASE + "v1/" + endpoint


def __v3_url(endpoint):
    return __URL_BASE + "v3/" + endpoint


def __log(msg):
    global __log_enabled
    if __log_enabled:
        print(msg)


__URLS = {
    # General
    "ping": __v1_url("ping"),
    "time": __v1_url("time"),

    # Market Data
    "depth": __v1_url("depth"),
    "agg_trades": __v1_url("aggTrades"),
    "candlesticks": __v1_url("klines"),
    "ticker_prices":  __v1_url("ticker/allPrices"),
    "ticker_books": __v1_url("ticker/allBookTickers"),
    "ticker_24hr": __v1_url("/ticker/24hr"),

    # Account
    "order": __v3_url("order"),
    "open_orders": __v3_url("openOrders"),
    "all_orders": __v3_url("allOrders"),
    "account": __v3_url("account"),
    "my_trades": __v3_url("myTrades")
}

OrderBook = namedtuple("OrderBook", "bids asks")

OrderBookTicker = namedtuple("OrderBookTicker", "bid_price, bid_qty, ask_price, ask_qty")

CandleStick = namedtuple("CandleStick", "open_time open high low close volume close_time quote_asset_volume trade_count taker_buy_base_quote_vol taker_buy_quote_asset_vol")


def __geturl_json(url, query_params={}, sign=False, method="GET"):
    if query_params is not None:
        for key in list(query_params.keys()):
            if query_params[key] is None:
                del query_params[key]

        if sign:
            query_params["timestamp"] = __timestamp()

            query = urllib.parse.urlencode(query_params)
            query_params["signature"] = hmac.new(__api_secret_key.encode("utf8"), query.encode("utf8"), digestmod=hashlib.sha256).hexdigest()

        url += "?" + urllib.parse.urlencode(query_params)

    __log("GET: " + url)

    req = urllib.request.Request(url, method=method)

    if sign:

        req.add_header("X-MBX-APIKEY", __api_key)

    json_ret = {}

    try:
        resp = urllib.request.urlopen(req, context=ctx)
        json_ret = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        # TODO: need to throw too, and need to get the json returned for better error msg
        __log(e.read())
        __log(e, " - ", url)

    return json_ret



# Public API (no authentication required)

def set_api_key(key, secret):
    """ Set the API key and the API secret Key
    If you don't have a key, log into binance.com and create one at https://www.binance.com/userCenter/createApi.html
    Be sure to never commit your keys to source control

    :param key: The API Key from your Binance account
    :param secret: The API Secret Key from your Binance account (case sensitive)
    :return: None
    """

# TODO:
def set_receive_window(millis):
    return None

def enable_logging(enabled):
    """ Enable or Disable logging
    :param enabled: True to turn logging on, false to turn it off
    :return: None
    """

    global __log_enabled
    __log_enabled = enabled


def ping():
    """ Ping Binance.com to see if it's online and we can hit it
    :return: True if pint was success, False otherwise
    """

    return __geturl_json(__URLS["ping"]) == {}


def server_time():
    """
    Get the current server time
    :return: Datetime object with the current server time
    """
    data = __geturl_json(__URLS["time"])
    return datetime.datetime.fromtimestamp(data["serverTime"] / 1000.0)


def order_book(symbol, limit=None):
    """ Get the order book for a given market symbol

    :param symbol: The market symbol (ie: BNBBTC)
    :param limit: (default 100, max 100, optional)
    :return: OrderBook tuple instance, containing the bids and asks
    """

    data = __geturl_json(__URLS["depth"], {"symbol": symbol, "limit": limit})

    bids = []
    asks = []
    for bid in data["bids"]:
        price_qty = (Decimal(bid[0]), Decimal(bid[1]))
        bids.append(price_qty)

    for ask in data["asks"]:
        price_qty = (Decimal(ask[0]), Decimal(ask[1]))
        asks.append(price_qty)

    book = OrderBook(bids, asks)

    return book


def aggregate_trades(symbol, from_id=None, start_time=None, end_time=None, limit=None):
    """ Get compressed, aggregate trades. Trades that fill at the time, from the same order,
    with the same price will have the quantity aggregated.

    If both startTime and endTime are sent, limit should not be sent AND the distance between
    startTime and endTime must be less than 24 hours.

    :param symbol: The market symbol (ie: BNBBTC)
    :param from_id: ID to get aggregate trades from INCLUSIVE (optional)
    :param start_time: Timestamp in ms to get aggregate trades from INCLUSIVE (optional)
    :param end_time: Timestamp in ms to get aggregate trades until INCLUSIVE (optional)
    :param limit: (Default 500; max 500, optional)
    :return:
    """

    params = {
        "symbol": symbol,
        "fromId": from_id,
        "startTime": start_time,
        "endTime": end_time,
        "limit": limit}

    trades = __geturl_json(__URLS["agg_trades"], params)

    # convert price and quantity to decimals
    for trade in trades:
        trade["p"] = Decimal(trade["p"])
        trade["q"] = Decimal(trade["q"])

    return trades


def candlesticks(symbol, interval, limit=None, start_time=None, end_time=None):
    """ Get Kline/candlestick bars for a symbol.
    Klines are uniquely identified by their open time.

    :param symbol: The market symbol (ie: BNBBTC)
    :param interval: one of (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
    :param limit: number of entries to return (Default 500; max 500, optional)
    :param start_time: Timestamp in ms to get candles from INCLUSIVE (optional)
    :param end_time: Timestamp in ms to get candles until INCLUSIVE(optional)
    :return: an array of CandleStick tuples
    """

    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
        "startTime": start_time,
        "endTime": end_time
    }

    candles = __geturl_json(__URLS["candlesticks"], params)
    for i in range(len(candles)):
        candles[i] = candles[i][:-1]
        for j in range(len(candles[i])):
            if isinstance(candles[i][j], str):
                candles[i][j] = Decimal(candles[i][j])

        candles[i] = CandleStick(*candles[i])

    return candles


def ticker_prices():
    """ Get the latest prices for all market symbols
    :return: a dict mapping the market symbols to prices
    """

    coins = __geturl_json(__URLS["ticker_prices"])

    prices = {}
    for coin in coins:
        prices[coin["symbol"]] = Decimal(coin["price"])

    return prices


def ticker_order_books():
    """ Gets the best price/quantity on the order book for all market symbols
    :return: an array of OrderBookTicker tuples (bid_price, bid_qty, ask_price, ask_qty)
    """
    coins = __geturl_json(__URLS["ticker_books"])

    book_tickers = {}
    for coin in coins:
        book_tickers[coin["symbol"]] = {
            OrderBookTicker(
                Decimal(coin["bidPrice"]),
                Decimal(coin["bidQty"]),
                Decimal(coin["askPrice"]),
                Decimal(coin["askQty"])
            )
        }

    return book_tickers


def ticker_24hr(symbol):
    """
    Gets the 24 hour price change statistics for a give market symbol
    :param symbol: the market symbol (ie: BNBBTC)
    :return: a dict containing statistics for the last 24 hour period
    """

    ticker = __geturl_json(__URLS["ticker_24hr"], {"symbol": symbol})

    for key in ticker:
        if isinstance(ticker[key], str):
            ticker[key] = Decimal(ticker[key])

    return ticker

# TODO: we can maybe just make recv window a global param


# Private account API, signing required

def new_order(symbol, side, type, quantity, price, new_client_order_id=None, stop_price=None, iceberg_qty=None):
    """ Submit a new order

    :param symbol: the market symbol (ie: BNBBTC)
    :param side: "BUY" or "SELL"
    :param type: "LIMIT" or "MARKET"
    :param quantity: the amount to buy/sell
    :param price: the price to buy/sell at
    :param new_client_order_id: A unique id for the order. Automatically generated if not sent (optional)
    :param stop_price: Used with stop orders (optional)
    :param iceberg_qty: Used with iceberg orders (optional)
    :return: # TODO:
    """

    params = {
        "symbol": symbol,
        "side": side,
        "type": type,
        "timeInForce": "GTC",       # TODO: does this need config?
        "quantity": quantity,
        "price": price,
        "newClientOrderId": new_client_order_id,
        "stopPrice": stop_price,
        "icebergQty": iceberg_qty,
        #"recvWindow": recv_window # TODO:
    }

    return __geturl_json(__URLS["order"], params, True, "POST")


def query_order(symbol, order_id=None, orig_client_order_id=None):
    """ Check an order's status
    Either order_id or orig_client_order_id must be sent

    :param symbol: the market symbol (ie: BNBBTC)
    :param order_id: the order id if orig_client_order_id isn't known
    :param orig_client_order_id: the client order id, if order id isn't known
    :return: a dict containing information about the order, if found
    """

    if order_id is None and orig_client_order_id is None:
        raise Exception("param Error: must specify orderId or origClientOrderId")

    params = {
        "symbol": symbol,
        "orderId": order_id,
        "origClientOrderId": orig_client_order_id,
        #"recvWindow": recv_window
    }

    return __geturl_json(__URLS["order"], params, True)


def cancel_order(symbol, order_id=None, orig_client_order_id=None, new_client_order_id=None):
    """ Cancel an active order
    Either order_id or orig_client_order_id must be sent

    :param symbol the market symbol (ie: BNBBTC):
    :param order_id: the order id if orig_client_order_id isn't known
    :param orig_client_order_id: the client order id, if order id isn't known
    :param new_client_order_id: Used to uniquely identify this cancel. Automatically generated by default (optiona)
    :return: a dict containing information about the cancelled order, if it existed
    """

    if order_id is None and orig_client_order_id is None:
        raise Exception("param Error: must specify orderId or origClientOrderId")

    params = {
        "symbol": symbol,
        "orderId": order_id,
        "origClientOrderId": orig_client_order_id,
        "newClientOrderId": new_client_order_id,
        #"recvWindow": recv_window
    }

    return __geturl_json(__URLS["order"], params, True, method="DELETE")


def open_orders(symbol):
    """ Gets all the open orders for a given symbol

    :param symbol: the market symbol (ie: BNBBTC)
    :return: an array of dicts containing info about all the open orders
    """

    return __geturl_json(__URLS["open_orders"], {"symbol": symbol}, True)


def all_orders(symbol, order_id=None, limit=None):
    """ Get all account orders; active, canceled, or filled

    :param symbol: the market symbol (ie: BNBBTC)
    :param order_id: if set, it will get orders >= that orderId. Otherwise most recent orders are returned (optional)
    :param limit: the limit of orders to return (Default 500; max 500, optinal))
    :return: an array of dicts containing info about all the open orders
    """
    params = {
        "symbol": symbol,
        "orderId": order_id,
        "limit": limit
    }

    return __geturl_json(__URLS["all_orders"], params, True)


def account_info():
    """ gets account information
    :return: dict containing account information and all balances
    """
    return __geturl_json(__URLS["account"], sign=True)


def my_trades(symbol, limit=None, from_id=None):
    """ Get trades for a specific account and symbol

    :param symbol: te market symbol (ie: BNBBTC)
    :param limit: the max number of trades to get (Default 500; max 500, optional)
    :param from_id: TradeId to fetch from. Default gets most recent trades (optional)
    :return: an array of dicts containing the trade info
    """
    params = {
        "symbol": symbol,
        "limit": limit,
        "fromId": from_id
    }

    return __geturl_json(__URLS["my_trades"], params, True)
