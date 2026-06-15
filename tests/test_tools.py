# tests/test_tools.py
from tools import search_listings

# ── Tests for search_listings ─────────────────────────────────────────────────

# Query 1: basic description match — returns a non-empty list of listings.
def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

# Query 2: no-match query — returns an empty list, never raises.
def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []   # empty list, no exception

# Query 3: price ceiling — every result is within the max_price budget.
def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)

# Query 4: description + price ceiling — "vintage graphic tee under $30".
#          Expect tee/graphic listings priced at $30 or below, ranked by relevance.
def test_search_description_and_price():
    results = search_listings("vintage graphic tee", size=None, max_price=30)
    assert len(results) > 0
    assert all(item["price"] <= 30 for item in results)

# Query 5: description + size filter — "denim jeans" in size "M".
#          Expect only listings whose size contains "m" (case-insensitive, e.g. "S/M").
def test_search_size_filter():
    results = search_listings("denim jeans", size="M", max_price=None)
    assert all("m" in item["size"].lower() for item in results)

# Query 6: no-match query — nonsense keywords with a tiny budget.
#          Expect an empty list (no results), never an exception.
def test_search_no_match():
    results = search_listings("sequin ballgown tuxedo", size=None, max_price=1)
    assert results == []
