# tests/test_edge_cases.py
"""Edge-case checks: the three failure modes must return values, never raise."""
import sys

from tools import search_listings, suggest_outfit, create_fit_card
from agent import run_agent
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

try:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
except (AttributeError, ValueError):
    pass


def test_search_zero_results():
    print(search_listings('designer ballgown', size='XXS', max_price=5))
    print(run_agent('designer ballgown size XXS under $5', get_example_wardrobe())["error"])


def test_suggest_outfit_empty_wardrobe():
    results = search_listings('vintage graphic tee', size=None, max_price=50)
    print(suggest_outfit(results[0], get_empty_wardrobe()))


def test_create_fit_card_empty_outfit():
    results = search_listings('vintage graphic tee', size=None, max_price=50)
    print(create_fit_card('', results[0]))


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s"])
