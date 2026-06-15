# tests/test_tools.py
from tools import search_listings, suggest_outfit
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

# A sample listing used to style across the suggest_outfit tests.
SAMPLE_ITEM = {
    "id": "lst_test",
    "title": "Vintage Band Tee — Faded Grey",
    "description": "Soft, broken-in faded grey band tee with a worn graphic.",
    "category": "tops",
    "style_tags": ["vintage", "graphic", "band"],
    "size": "M",
    "condition": "good",
    "price": 19.0,
    "colors": ["grey"],
    "brand": None,
    "platform": "depop",
}

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


# ── Tests for suggest_outfit ──────────────────────────────────────────────────

# Wardrobe case 1: example wardrobe — the user already owns pieces.
#          Expect a non-empty string that references specific owned items.
def test_suggest_outfit_example_wardrobe():
    wardrobe = get_example_wardrobe()
    result = suggest_outfit(SAMPLE_ITEM, wardrobe)
    assert isinstance(result, str)
    assert result.strip() != ""
    # Should name at least one piece the user owns, not just generic advice.
    owned_names = [item["name"].lower() for item in wardrobe["items"]]
    assert any(name.split(",")[0] in result.lower() for name in owned_names)

# Wardrobe case 2: empty wardrobe — no pieces saved yet.
#          Expect general styling advice, never a crash or empty string.
def test_suggest_outfit_empty_wardrobe():
    result = suggest_outfit(SAMPLE_ITEM, get_empty_wardrobe())
    assert isinstance(result, str)
    assert result.strip() != ""
    # Falls back to the "style from scratch" general-advice opening.
    assert "wardrobe is empty" in result.lower()
