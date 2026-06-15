"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card


# ── query parsing ─────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """
    Extract a description, size, and max_price from a natural language query.

    Uses lightweight regex matching (no LLM call) so parsing is fast and
    deterministic:
        - max_price: first dollar amount, optionally preceded by "under"/"below".
        - size:      a "size X" phrase, or a standalone XS/S/M/L/XL/XXL token.
        - description: the query with the size/price phrases stripped out.
    """
    text = query.strip()

    # max_price: "$30", "under 30", "below $25.50"
    max_price = None
    price_match = re.search(
        r"(?:under|below|less than|max)?\s*\$?\s*(\d+(?:\.\d{1,2})?)", text, re.I
    )
    if price_match:
        max_price = float(price_match.group(1))

    # size: explicit "size M" or a standalone size token
    size = None
    size_match = re.search(r"\bsize\s+([a-z0-9]+)\b", text, re.I)
    if size_match:
        size = size_match.group(1).upper()
    else:
        token_match = re.search(r"\b(XXS|XS|S|M|L|XL|XXL|XXXL)\b", text)
        if token_match:
            size = token_match.group(1).upper()

    # description: strip the structured phrases so only the keywords remain
    description = text
    description = re.sub(
        r"(?:under|below|less than|max)?\s*\$?\s*\d+(?:\.\d{1,2})?", "", description, flags=re.I
    )
    description = re.sub(r"\bsize\s+[a-z0-9]+\b", "", description, flags=re.I)
    description = re.sub(r"\s+", " ", description).strip()

    return {
        "description": description or text,
        "size": size,
        "max_price": max_price,
    }


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.
    """

    # Step 1: Initialize the session.
    session = _new_session(query, wardrobe)

    # Step 2: Parse the query into description / size / max_price.
    session["parsed"] = _parse_query(query)

    # Step 3: Search listings. Bail out early if nothing matches.
    session["search_results"] = search_listings(
        description=session["parsed"]["description"],
        size=session["parsed"]["size"],
        max_price=session["parsed"]["max_price"],
    )
    if not session["search_results"]:
        session["error"] = (
            "No listings matched your search. Try loosening the size or price "
            "filters, or describing the item differently."
        )
        return session

    # Step 4: Select the top result.
    session["selected_item"] = session["search_results"][0]

    # Step 5: Suggest an outfit (handles empty wardrobe with general advice).
    session["outfit_suggestion"] = suggest_outfit(
        session["selected_item"], session["wardrobe"]
    )

    # Step 6: Create the shareable fit card.
    session["fit_card"] = create_fit_card(
        session["outfit_suggestion"], session["selected_item"]
    )

    # Step 7: Return the completed session.
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
