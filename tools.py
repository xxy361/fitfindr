"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import re

from groq import Groq

from config import GROQ_API_KEY, LLM_MODEL
from utils.data_loader import load_listings


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from config."""
    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=GROQ_API_KEY)


def _new_item_summary(item: dict) -> str:
    """Compact description of the thrifted item for use in prompts."""
    parts = [
        f"{item.get('title', 'item')}",
        f"category: {item.get('category', 'unknown')}",
        f"colors: {', '.join(item.get('colors', [])) or 'n/a'}",
        f"style: {', '.join(item.get('style_tags', [])) or 'n/a'}",
    ]
    if item.get("brand"):
        parts.append(f"brand: {item['brand']}")
    if item.get("description"):
        parts.append(f"details: {item['description']}")
    return " | ".join(parts)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform
    """
    
    # 1. Load all listings with load_listings().
    listings = load_listings()

    # Keywords from the description, lowercased and deduped.
    keywords = set(re.findall(r"[a-z0-9]+", description.lower()))

    size_query = size.strip().lower() if size else None

    scored: list[tuple[int, dict]] = []
    for listing in listings:
        # 2.  Filter by max_price and size (if provided).
        if max_price is not None and listing["price"] > max_price:
            continue
        if size_query is not None and size_query not in listing["size"].lower():
            continue

        # 3. Score each remaining listing by keyword overlap with `description`.
        haystack = " ".join(
            [
                listing["title"],
                listing["description"],
                listing["category"],
                " ".join(listing["style_tags"]),
                " ".join(listing["colors"]),
                listing["brand"] or "",
            ]
        ).lower()
        haystack_words = set(re.findall(r"[a-z0-9]+", haystack))
        score = len(keywords & haystack_words)

        # 4. Drop any listings with a score of 0 (no relevant matches).
        if score > 0:
            scored.append((score, listing))

    # 5. Sort by score, highest first, and return the listing dicts.
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [listing for _, listing in scored[:3]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.
    """
    
    client = _get_groq_client()
    item_text = _new_item_summary(new_item)

    # 1. Check whether wardrobe['items'] is empty.
    items = (wardrobe or {}).get("items", [])

    if not items:
        # 2. Empty wardrobe: ask the LLM for general styling advice on the item.
        system = (
            "You are FitFindr, a friendly personal stylist. The user has no "
            "wardrobe items saved yet, so give general styling advice for the new "
            "piece: what kinds of items pair well with it, what vibe it suits, and "
            "how to build a look from scratch. Keep it warm and concise (2-4 "
            "sentences). Start with: \"Looks like your wardrobe is empty here, so "
            "here's how I'd style this piece from scratch:\""
        )
        user = f"New item — {item_text}"
    else:
        # 3. Non-empty wardrobe: format owned pieces and ask for specific combos.
        wardrobe_lines = []
        for w in items:
            line = f"- {w.get('name', 'item')} ({w.get('category', '')})"
            if w.get("colors"):
                line += f", colors: {', '.join(w['colors'])}"
            if w.get("style_tags"):
                line += f", style: {', '.join(w['style_tags'])}"
            if w.get("notes"):
                line += f", notes: {w['notes']}"
            wardrobe_lines.append(line)
        wardrobe_text = "\n".join(wardrobe_lines)

        system = (
            "You are FitFindr, a friendly personal stylist. Suggest 1-2 "
            "complete outfits that pair the NEW item with specific pieces the user "
            "already owns. Name the wardrobe pieces explicitly, describe the vibe, "
            "and add a short styling note. Keep it warm and concise."
        )
        user = (
            f"New item — {item_text}\n\n"
            f"User's wardrobe:\n{wardrobe_text}"
        )

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.7,
    )

    # 4. Return the LLM's response as a string.
    advice = response.choices[0].message.content.strip()

    # For the empty-wardrobe case, guarantee the response ends with 😎
    # regardless of what the LLM returns.
    if not items and not advice.endswith("😎"):
        advice = f"{advice} 😎"

    return advice


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)
    """

    # 1. Guard against an empty or whitespace-only outfit string.
    if not outfit or not outfit.strip():
        return (
            "I couldn't whip up a caption without an outfit to work from — "
            "let's find you a piece first and I'll make it shareable! ✨"
        )

    client = _get_groq_client()

    name = new_item.get("title", "this piece")
    price = new_item.get("price")
    price_text = f"${price:g}" if price is not None else "a steal"
    platform = new_item.get("platform", "secondhand")

    # 2. Build a prompt with the item details and the outfit suggestion.
    system = (
        "You are FitFindr, writing short, shareable OOTD captions for social "
        "media (Instagram/TikTok). Write 2-3 sentences that sound casual and "
        "authentic — like a real outfit post, not a product description. "
        "Naturally mention the item's name, price, and platform once each, the "
        "owned pieces it's paired with, and capture the outfit's vibe in specific "
        "terms. A couple of emojis are welcome."
    )
    user = (
        f"New item: {name} — {price_text} on {platform}\n\n"
        f"Outfit suggestion:\n{outfit.strip()}\n\n"
        "Write the caption."
    )

    # 3. Call the LLM (higher temperature for variety) and return the caption.
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.9,
    )
    return response.choices[0].message.content.strip()
