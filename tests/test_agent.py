# tests/test_agent.py
"""
State-flow tests for the agent planning loop.

These verify that data produced by one step is the *same object* consumed by the
next — using identity (`is`), not equality. If the agent were re-prompting the
user or substituting hardcoded values between steps, these identity checks would
fail even when the printed values happened to look right.

Every tool call, its inputs, and its outputs are printed to the console so the
state handoffs are visible. Run with -s to see the trace:

    python -m pytest tests/test_agent.py -v -s
    # or just: python tests/test_agent.py

The happy-path test calls the real LLM (like test_tools.py), so it needs a valid
GROQ_API_KEY.
"""
import sys

import agent
from utils.data_loader import get_example_wardrobe

# Windows consoles default to cp1252, which can't encode emoji in LLM output.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

# The "Complete Interaction" example query from planning.md.
EXAMPLE_QUERY = (
    "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans "
    "and chunky sneakers. What's out there and how would I style it?"
)


def _rule(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def test_state_flows_by_reference(monkeypatch):
    """selected_item → suggest_outfit → outfit_suggestion → create_fit_card,
    all passed by reference with nothing fabricated in between."""
    captured = {}

    real_search = agent.search_listings
    real_suggest = agent.suggest_outfit
    real_card = agent.create_fit_card

    def spy_search(description, size=None, max_price=None):
        _rule("TOOL CALL: search_listings")
        print(f"  INPUT  description={description!r} size={size!r} max_price={max_price!r}")
        results = real_search(description, size, max_price)
        print(f"  OUTPUT {len(results)} listing(s):")
        for i, r in enumerate(results):
            print(f"    [{i}] id={r['id']!r:14} title={r['title']!r} ${r['price']:g}")
        captured["search_return"] = results
        return results

    def spy_suggest(new_item, wardrobe):
        _rule("TOOL CALL: suggest_outfit")
        print(f"  INPUT  new_item id={new_item['id']!r} title={new_item['title']!r}")
        print(f"         new_item object id = {id(new_item)}")
        print(f"         wardrobe items: {len(wardrobe.get('items', []))}")
        captured["suggest_new_item"] = new_item        # what selected_item became
        result = real_suggest(new_item, wardrobe)
        print(f"  OUTPUT outfit_suggestion (object id = {id(result)}):")
        print(f"    {result}")
        captured["suggest_return"] = result
        return result

    def spy_card(outfit, new_item):
        _rule("TOOL CALL: create_fit_card")
        print(f"  INPUT  outfit (object id = {id(outfit)}):")
        print(f"    {outfit}")
        print(f"  INPUT  new_item id={new_item['id']!r} (object id = {id(new_item)})")
        captured["card_outfit"] = outfit               # what outfit_suggestion became
        captured["card_new_item"] = new_item
        result = real_card(outfit, new_item)
        print(f"  OUTPUT fit_card:")
        print(f"    {result}")
        return result

    monkeypatch.setattr(agent, "search_listings", spy_search)
    monkeypatch.setattr(agent, "suggest_outfit", spy_suggest)
    monkeypatch.setattr(agent, "create_fit_card", spy_card)

    _rule(f"RUN AGENT  query={EXAMPLE_QUERY!r}")
    session = agent.run_agent(query=EXAMPLE_QUERY, wardrobe=get_example_wardrobe())

    _rule("FINAL SESSION STATE")
    print(f"  parsed            : {session['parsed']}")
    print(f"  selected_item     : (object id = {id(session['selected_item'])})")
    print(f"    {session['selected_item']}")
    print(f"  outfit_suggestion : (object id = {id(session['outfit_suggestion'])})")
    print(f"    {session['outfit_suggestion']}")
    print(f"  fit_card          : {session['fit_card']}")
    print(f"  error             : {session['error']}")

    _rule("STATE-FLOW IDENTITY CHECKS  (is, not ==)")
    c1 = session["selected_item"] is session["search_results"][0]
    c2 = session["selected_item"] is captured["suggest_new_item"]
    c3 = session["outfit_suggestion"] is captured["suggest_return"]
    c4 = session["outfit_suggestion"] is captured["card_outfit"]
    c5 = session["selected_item"] is captured["card_new_item"]
    print(f"  [{'PASS' if c1 else 'FAIL'}] selected_item IS search_results[0] (top result, not hardcoded)")
    print(f"  [{'PASS' if c2 else 'FAIL'}] selected_item IS the dict passed into suggest_outfit")
    print(f"  [{'PASS' if c3 else 'FAIL'}] suggest_outfit's return IS session['outfit_suggestion']")
    print(f"  [{'PASS' if c4 else 'FAIL'}] outfit_suggestion IS the string passed into create_fit_card")
    print(f"  [{'PASS' if c5 else 'FAIL'}] selected_item IS the dict passed into create_fit_card")
    print("=" * 70)

    # The loop completed without an early exit.
    assert session["error"] is None
    assert c1 and c2 and c3 and c4 and c5


def test_no_results_skips_downstream_tools(monkeypatch):
    """On empty search results the loop must NOT call suggest_outfit /
    create_fit_card, and must leave their session fields as None."""
    calls = []
    monkeypatch.setattr(agent, "suggest_outfit",
                        lambda *a, **k: calls.append("suggest"))
    monkeypatch.setattr(agent, "create_fit_card",
                        lambda *a, **k: calls.append("card"))

    _rule("RUN AGENT  (no-results path)")
    session = agent.run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"  search_results    : {session['search_results']}")
    print(f"  downstream calls  : {calls}")
    print(f"  selected_item     : {session['selected_item']}")
    print(f"  outfit_suggestion : {session['outfit_suggestion']}")
    print(f"  fit_card          : {session['fit_card']}")
    print(f"  error             : {session['error']}")
    print("=" * 70)

    assert session["search_results"] == []
    assert session["error"] is not None
    assert calls == []                          # neither downstream tool ran
    assert session["selected_item"] is None
    assert session["outfit_suggestion"] is None
    assert session["fit_card"] is None


if __name__ == "__main__":
    # Allow running directly (prints show without pytest's capture).
    import pytest
    pytest.main([__file__, "-v", "-s"])
