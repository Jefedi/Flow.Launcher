# -*- coding: utf-8 -*-
"""Currency + crypto conversion for Calculate Anything.

Design: every code is priced in USD ("USD backbone"), so any pair works the same
way -- fiat<->fiat, crypto<->fiat, crypto<->crypto:

    value = amount * usd_value_of(src) / usd_value_of(dst)

Data sources (free, no API key):
  * Fiat   -> Frankfurter (ECB)  https://api.frankfurter.app/latest?from=USD
  * Crypto -> CoinGecko          https://api.coingecko.com/api/v3/simple/price

Rates are cached on disk with a TTL so we don't hit the network on every
keystroke. Knows nothing about Flow Launcher.
"""

import json
import os
import re
import tempfile
import time
import urllib.error
import urllib.request
from collections import namedtuple

HTTP_TIMEOUT = 5
FIAT_TTL = 3600    # 1 hour
CRYPTO_TTL = 300   # 5 minutes

ConversionResult = namedtuple(
    "ConversionResult", ["amount", "src", "dst", "value", "unit_rate"]
)


class ConversionError(Exception):
    """Raised with a readable message when a conversion cannot be made."""


# --- Known currencies -------------------------------------------------------

# Fiat codes available from Frankfurter (ECB reference set).
FIAT_CODES = {
    "AUD", "BGN", "BRL", "CAD", "CHF", "CNY", "CZK", "DKK", "EUR", "GBP",
    "HKD", "HUF", "IDR", "ILS", "INR", "ISK", "JPY", "KRW", "MXN", "MYR",
    "NOK", "NZD", "PHP", "PLN", "RON", "SEK", "SGD", "THB", "TRY", "USD", "ZAR",
}

# Crypto symbol -> CoinGecko id (top coins).
CRYPTO_IDS = {
    "BTC": "bitcoin", "ETH": "ethereum", "USDT": "tether", "BNB": "binancecoin",
    "SOL": "solana", "USDC": "usd-coin", "XRP": "ripple", "ADA": "cardano",
    "DOGE": "dogecoin", "TRX": "tron", "DOT": "polkadot", "MATIC": "matic-network",
    "LTC": "litecoin", "BCH": "bitcoin-cash", "LINK": "chainlink", "XLM": "stellar",
    "AVAX": "avalanche-2", "ATOM": "cosmos", "UNI": "uniswap", "XMR": "monero",
    "ETC": "ethereum-classic", "FIL": "filecoin", "APT": "aptos", "ARB": "arbitrum",
    "OP": "optimism", "NEAR": "near", "ALGO": "algorand", "VET": "vechain",
    "ICP": "internet-computer", "SHIB": "shiba-inu", "PEPE": "pepe", "TON": "the-open-network",
}

# Symbol -> code aliases.
SYMBOLS = {
    "$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY", "₿": "BTC",
    "US$": "USD", "R$": "BRL", "₹": "INR", "₩": "KRW",
}


def resolve_code(token):
    """Return canonical currency/crypto code for a token, or None if unknown."""
    if not token:
        return None
    t = token.strip()
    if t in SYMBOLS:
        return SYMBOLS[t]
    up = t.upper()
    if up in SYMBOLS:
        return SYMBOLS[up]
    if up in FIAT_CODES or up in CRYPTO_IDS:
        return up
    return None


def is_currency(token):
    return resolve_code(token) is not None


# --- Disk cache -------------------------------------------------------------

def _cache_path():
    base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    folder = os.path.join(base, "FlowLauncher", "CalculateAnything")
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        folder = tempfile.gettempdir()
    return os.path.join(folder, "rates_cache.json")


def _load_cache():
    try:
        with open(_cache_path(), "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _save_cache(cache):
    try:
        with open(_cache_path(), "w", encoding="utf-8") as fh:
            json.dump(cache, fh)
    except OSError:
        pass  # cache is best-effort


# --- HTTP -------------------------------------------------------------------

def _get_json(url):
    # Some rate providers' WAFs reject the default "Python-urllib" UA with 403.
    request = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Calculate Anything Flow Launcher plugin)",
    })
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise ConversionError("Limite d'API atteinte, réessaie dans un instant")
        raise ConversionError(f"HTTP {exc.code}")
    except urllib.error.URLError as exc:
        raise ConversionError(f"Réseau indisponible ({exc.reason})")
    except TimeoutError:
        raise ConversionError("Délai dépassé")
    except ValueError:
        raise ConversionError("Réponse invalide du service de taux")


# --- USD pricing ------------------------------------------------------------

def _fiat_per_usd(cache):
    """Map of fiat code -> units per 1 USD (cached)."""
    entry = cache.get("fiat")
    if entry and (time.time() - entry.get("ts", 0)) < FIAT_TTL:
        return entry["data"]
    data = _get_json("https://api.frankfurter.app/latest?from=USD")
    rates = data.get("rates", {})
    rates["USD"] = 1.0
    cache["fiat"] = {"ts": time.time(), "data": rates}
    return rates


def _crypto_usd(cache, ids):
    """Map of CoinGecko id -> USD price, fetching any not freshly cached."""
    store = cache.setdefault("crypto", {})
    now = time.time()
    missing = [i for i in ids
               if not (store.get(i) and (now - store[i].get("ts", 0)) < CRYPTO_TTL)]
    if missing:
        url = ("https://api.coingecko.com/api/v3/simple/price"
               f"?ids={','.join(missing)}&vs_currencies=usd")
        data = _get_json(url)
        for cid in missing:
            price = (data.get(cid) or {}).get("usd")
            if price is not None:
                store[cid] = {"ts": now, "usd": float(price)}
    return {i: store[i]["usd"] for i in ids if i in store}


def _usd_value_of(code, cache):
    """USD value of one unit of ``code`` (fiat or crypto)."""
    if code in CRYPTO_IDS:
        cid = CRYPTO_IDS[code]
        prices = _crypto_usd(cache, [cid])
        if cid not in prices:
            raise ConversionError(f"Prix indisponible pour {code}")
        return prices[cid]
    # fiat
    rates = _fiat_per_usd(cache)
    if code not in rates:
        raise ConversionError(f"Devise non supportée : {code}")
    return 1.0 / float(rates[code])


# --- Public API -------------------------------------------------------------

def convert(amount, src_token, dst_token):
    """Convert ``amount`` of ``src`` into ``dst``. Returns a ConversionResult."""
    src = resolve_code(src_token)
    dst = resolve_code(dst_token)
    if src is None:
        raise ConversionError(f"Devise inconnue : {src_token}")
    if dst is None:
        raise ConversionError(f"Devise inconnue : {dst_token}")

    cache = _load_cache()
    src_usd = _usd_value_of(src, cache)
    dst_usd = _usd_value_of(dst, cache)
    _save_cache(cache)

    if dst_usd == 0:
        raise ConversionError("Taux invalide")

    unit_rate = src_usd / dst_usd
    return ConversionResult(amount, src, dst, amount * unit_rate, unit_rate)


# --- Query parsing ----------------------------------------------------------

# e.g. "10 usd in eur", "0.5 btc to usd", "$100 in eur", "100usd eur", "usd in eur"
_QUERY_RE = re.compile(
    r"""^\s*
        (?P<amount>[-+]?[\d][\d,\s]*\.?\d*)?\s*
        (?P<src>\$|€|£|¥|₿|R\$|US\$|₹|₩|[A-Za-z]{2,5})\s*
        (?:(?:in|to|as|into|=|->)\s+)?
        (?P<dst>\$|€|£|¥|₿|R\$|US\$|₹|₩|[A-Za-z]{2,5})?
        \s*$""",
    re.IGNORECASE | re.VERBOSE,
)


def parse_query(text, default_currency="EUR"):
    """Parse a currency query into (amount, src, dst), or return None.

    Only succeeds when ``src`` resolves to a known currency/crypto, so it is safe
    to try before the math engine. ``dst`` defaults to ``default_currency``.
    """
    text = text or ""
    # Normalize a leading symbol+amount ("$100 in eur" -> "100 USD in eur").
    lead = re.match(r"\s*(\$|€|£|¥|₿|R\$|US\$|₹|₩)\s*([\d.,]+)(.*)$", text)
    if lead:
        text = f"{lead.group(2)} {SYMBOLS[lead.group(1)]} {lead.group(3)}"

    m = _QUERY_RE.match(text)
    if not m:
        return None

    src = resolve_code(m.group("src"))
    if src is None:
        return None

    dst_token = m.group("dst")
    dst = resolve_code(dst_token) if dst_token else resolve_code(default_currency)
    if dst is None:
        return None

    # A bare "<code>" with no amount and no target is ambiguous with constants
    # like "e"; require either an amount or an explicit target.
    if m.group("amount") is None and not dst_token:
        return None

    amount_raw = m.group("amount")
    if amount_raw is None:
        amount = 1.0
    else:
        try:
            amount = float(amount_raw.replace(",", "").replace(" ", ""))
        except ValueError:
            return None

    if src == dst:
        return None  # nothing to convert; let math/other handlers try

    return amount, src, dst
