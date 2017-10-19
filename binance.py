import urllib.request
import urllib.parse
import json
import ssl
import datetime
import hmac
import hashlib
import time


# TODO: figure out how to make SSL work and get ride of this
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

URL_BASE = "https://www.binance.com/api/"

api_key = None
api_secret_key = None


def timestamp():
    return int(round(time.time() * 1000))


def v1_url(endpoint):
    return URL_BASE + "v1/" + endpoint


def v3_url(endpoint):
    return URL_BASE + "v3/" + endpoint


URLS = {
    # General
    "ping": v1_url("ping"),
    "time": v1_url("time"),

    # Market Data
    "depth": v1_url("depth"),
    "agg_trades": v1_url("aggTrades"),
    "candlesticks": v1_url("klines"),
    "ticker_prices":  v1_url("ticker/allPrices"),
    "ticker_books": v1_url("ticker/allBookTickers"),
    "ticker_24hr": v1_url("/ticker/24hr"),

    # Account
    "order": v3_url("order"),
    "open_orders": v3_url("openOrders"),
    "all_orders": v3_url("allOrders"),
    "account": v3_url("account"),
    "my_trades": v3_url("myTrades")
}


def geturl_json(url, query_params={}, sign=False, method="GET"):
    if query_params is not None:
        for key in list(query_params.keys()):
            if query_params[key] is None:
                del query_params[key]

        if sign:
            query_params["timestamp"] = timestamp()

            query = urllib.parse.urlencode(query_params)
            query_params["signature"] = hmac.new(api_secret_key.encode("utf8"), query.encode("utf8"), digestmod=hashlib.sha256).hexdigest()

        url += "?" + urllib.parse.urlencode(query_params)

    print("GET: ", url)

    req = urllib.request.Request(url, method=method)

    if sign:

        req.add_header("X-MBX-APIKEY", api_key)

    json_ret = {}

    try:
        resp = urllib.request.urlopen(req, context=ctx)
        json_ret = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        # TODO: need to throw too, and need to get the json returned for better error msg
        print(e.read())
        print(e, " - ", url)

    return json_ret


def set_api_key(key, secret):
    global api_key
    global api_secret_key

    api_key = key
    api_secret_key = secret


def ping():
    return geturl_json(URLS["ping"]) == {}


def get_server_time():
    data = geturl_json(URLS["time"])
    return datetime.datetime.fromtimestamp(data["serverTime"] / 1000.0)


# symbol: required
# limit: Default 100; max 100.
def get_depth(symbol, limit=None):
    return geturl_json(URLS["depth"], {"symbol": symbol, "limit": limit})


def get_aggtrades(symbol, from_id=None, start_time=None, end_time=None, limit=None):
    params = {
        "symbol": symbol,
        "fromId": from_id,
        "startTime": start_time,
        "endTime": end_time,
        "limit": limit}

    return geturl_json(URLS["agg_trades"], params)


def get_candlesticks(symbol, interval, limit=None, start_time=None, end_time=None):
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
        "startTime": start_time,
        "endTime": end_time
    }

    return geturl_json(URLS["candlesticks"], params)


def get_prices():
    coins = geturl_json(URLS["ticker_prices"])

    prices = {}
    for coin in coins:
        prices[coin["symbol"]] = coin["price"]

    return prices


def get_book_tickers():
    coins = geturl_json(URLS["ticker_books"])

    book_tickers = {}
    for coin in coins:
        book_tickers[coin["symbol"]] = {
            "bidPrice": coin["bidPrice"],
            "bidQty": coin["bidQty"],
            "askPrice": coin["askPrice"],
            "askQty": coin["askQty"]
        }

    return book_tickers


def get_prevday(symbol):
    return geturl_json(URLS["ticker_24hr"], {"symbol": symbol})


# TODO: we can maybe just make recv window a global param


def new_order(symbol, side, type, quantity, price, new_client_order_id=None, stop_price=None, iceberg_qty=None, recv_window=None):
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
        "recvWindow": recv_window
    }

    return geturl_json(URLS["order"], params, True, "POST")


def query_order(symbol, order_id=None, orig_client_order_id=None, recv_window=None):
    if order_id is None and orig_client_order_id is None:
        raise Exception("param Error: must specify orderId or origClientOrderId")

    params = {
        "symbol": symbol,
        "orderId": order_id,
        "origClientOrderId": orig_client_order_id,
        "recvWindow": recv_window
    }

    return geturl_json(URLS["order"], params, True)


def cancel_order(symbol, order_id=None, orig_client_order_id=None, new_client_order_id=None, recv_window=None):
    if order_id is None and orig_client_order_id is None:
        raise Exception("param Error: must specify orderId or origClientOrderId")

    params = {
        "symbol": symbol,
        "orderId": order_id,
        "origClientOrderId": orig_client_order_id,
        "newClientOrderId": new_client_order_id,
        "recvWindow": recv_window
    }

    return geturl_json(URLS["order"], params, True, method="DELETE")


def open_orders(symbol):
    return geturl_json(URLS["open_orders"], {"symbol": symbol}, True)


def all_orders(symbol, order_id=None, limit=None):
    params = {
        "symbol": symbol,
        "orderId": order_id,
        "limit": limit
    }

    return geturl_json(URLS["all_orders"], params, True)


def account_info():
    return geturl_json(URLS["account"], sign=True)


def my_trades(symbol, limit=None, from_id=None):
    params = {
        "symbol": symbol,
        "limit": limit,
        "fromId": from_id
    }

    return geturl_json(URLS["my_trades"], params, True)
