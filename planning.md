# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

### Tool 1: search_listings

**What it does:**

Search the listings dataset for items that match the user description with optional filters of size and price ceiling. Return the best matches ranked by relevance.

**Input parameters:**

- `description` (str): text description of the wanted item to search in the dataset
- `size` (str): optional filter, listings not in this size are filtered out
- `max_price` (float): optional filter, listings above this price are filtered out

**What it returns:**

A list of dicts that has up to 3 listings (dicts) that match the description sorted by descending relevance. Each listing is a dict that contains the following fields:
- `id` (str): unique listing ID
- `title` (str): item name, e.g. "Faded Band Tee"
- `description` (str): item description text
- `category` (str): item type, e.g. "tops", "shoes"
- `style_tags` (list[str]): descriptive keywords, e.g. ["vintage","graphic","band"]
- `size` (str): e.g. "M"
- `condition` (str): e.g. "Good", "Like New"
- `price` (float): dollars, e.g. 22.0
- `colors` (list[str]): e.g. ["black","white"]
- `brand` (str): e.g. "Hanes", or "Unbranded"
- `platform` (str): source marketplace, e.g. "Depop"

**What happens if it fails or returns nothing:**

Returns an empty [] when no match is found.

---

### Tool 2: suggest_outfit

**What it does:**

Given one specific item and the user's wardrobe, generates outfit combinations that pairs the new item with pieces that the user already owns.

**Input parameters:**

- `new_item` (dict): the item being styled. Contains the follwing fields:
     - `id` (str): unique listing ID
     - `title` (str): item name, e.g. "Faded Band Tee"
     - `description` (str): item description text
     - `category` (str): item type, e.g. "tops", "shoes"
     - `style_tags` (list[str]): descriptive keywords, e.g. ["vintage","graphic","band"]
     - `size` (str): e.g. "M"
     - `condition` (str): e.g. "Good", "Like New"
     - `price` (float): dollars, e.g. 22.0
     - `colors` (list[str]): e.g. ["black","white"]
     - `brand` (str): e.g. "Hanes", or "Unbranded"
     - `platform` (str): source marketplace, e.g. "Depop"
- `wardrobe` (dict): the items owned by the user, could be empty. Contains the following fieds:
     - `id` (str): unique wardrobe-item ID
     - `name` (str): item name, e.g. "baggy jeans"
     - `category` (str): item type, e.g. "bottoms", "shoes"
     - `colors` (list[str]): e.g. ["blue"]
     - `style_tags` (list[str]): descriptive keywords, e.g. ["baggy","denim"]
     - `notes` (str): e.g. "high-waisted, slightly cropped"

**What it returns:**

If the wardrobe is not empty, returns a string that names the specific pieces from the wardrobe alongside the new item, with vibe and styling notes.

**What happens if it fails or returns nothing:**

If the wardrobe is emtpy, gives a string that gives general advice on the new item.

---

### Tool 3: create_fit_card

**What it does:**

Turns the outfit suggestion text plus the new item into a short, casual, shareable style caption for posting on social media.

**Input parameters:**

- `outfit` (str): The outfit suggestion string returned by `suggest_outfit()`
- `new_item` (dict): the listing dict for the new item, used to pull its name, price, and platform into the caption

**What it returns:**

A 2-3 sentence caption of the complete outfit that mentions the new item's name, price, and platform, the owned items that got paired with the new item, and the general vibe of the outfit.

**What happens if it fails or returns nothing:**

If the outfit string is empty, returns an error-message string that informs the user no outfit suggestion was provided.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->
<!-- Describe what this tool does in 1–2 sentences -->
<!-- List each parameter, its type, and what it represents -->
<!-- Describe the return value -->
<!-- What should the agent do if the outfit data is incomplete? -->
TBD

---

## Planning Loop

**How does your agent decide which tool to call next?**

When a session starts, the loop sends the user query plus all three tool schemas to the LLM, and a `session` dict tracks state. Each turn the model decides the tool call while the loop checks the result: 
1. after `search_listings`, if `search_results == []` it sets `session["error"]` and returns early (never calling `suggest_outfit` with no item), otherwise it sets `selected_item = search_results[0]` and re-invokes
2. after `suggest_outfit` it always stores `outfit_suggestion` (if empty wardrobe, returns general advice, no error and continue)
3. after `create_fit_card` it always stores `fit_card` (returns fallback string, no error and continue). 

Before each call the loop checks a `max_steps` cap and sets `error` if exceeded. The loop ends successfully when the model returns plain text with no `tool_calls`, or early when error is set or max steps is reached.

---

## State Management

**How does information from one tool get passed to the next?**

States within a session are tracked in a `session` dict which serves as the source of truth for the session. Each user interaction would write its output into the corresponding field in the `session` dict, and the next step would read from it to determine the next interaction and pass information to tool calls when needed. This `session` dict has the following data:
- `query`: original user query
- `parsed` (dict): extracted description / size / max_price
- `search_results` (list): list of matching listing dicts
- `selected_item`: top result, passed into suggest_outfit
- `wardrobe`: user's wardrobe dict
- `outfit_suggestion`: string returned by suggest_outfit
- `fit_card`: string returned by create_fit_card
- `error`: set if the interaction ended early

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Stops the loop and sets `session["error"]`, returns message to user: "Hmm, I couldn't find anything matching that right now. 😕" |
| suggest_outfit | Wardrobe is empty | Does not stop the loop or set error. The tool would give general outfit advice on the new item: "Looks like your wardrobe is empty here, so here's how I'd style this piece from scratch: pair it with <neutral basics / contrasting textures> and it'd give off a <vibe> look. 😎 " The loop continues. |
| create_fit_card | Outfit input is missing or incomplete | Returns a fallback string and does not set error: "I couldn't whip up a caption without an outfit to work from — let's find you a piece first and I'll make it shareable! ✨" |

---

## Architecture

```
                 User query + wardrobe
                          │
                          ▼
        ┌─────────────────────────────────────────┐
        │            PLANNING LOOP                │
        │   (send history + tool schemas to LLM)  │
        │                                         │◄─────────────┐
        └─────────────────────────────────────────┘              │
                          │                                      │
                          ▼                                      │
                 ┌──────────────────┐                            │
                 │   LLM decides    │                            │
                 └──────────────────┘                            │
                    │            │                               │
        tool_calls? │            │ plain text (no tool_calls)    │
                    ▼            └──────────────► DONE ──► Return session
        ┌───────────────────────┐                         (fit_card / error)
        │   Execute chosen tool │                                ▲
        └───────────────────────┘                                │
            │        │        │                                  │
            ▼        ▼        ▼                                  │
   search_listings  suggest_outfit  create_fit_card              │
            │        │        │                                  │
            │    (empty       (empty outfit                      │
            │   wardrobe →     → fallback                        │
            │  general advice) string)                           │
            ▼        ▼        ▼                                  │
        ┌─────────────────────────────────────────┐              │
        │              SESSION dict               │              │
        │  query · parsed · search_results ·      │              │
        │  selected_item · wardrobe ·             │── append ────┘
        │  outfit_suggestion · fit_card · error   │  result to
        └─────────────────────────────────────────┘  history,
                          │                          re-invoke LLM
          error set / max_steps reached
                          │
                          ▼
                   Return session (early exit)
```

---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**

I'll give Claude my Tool 1 specs in this document and ask it to implement the `search_listings()` tool and use the `load_listings()` from the data loader. I'll ask Claude to generate 3 queries for tests.

I'll give Claude the Tool 2 spec to implement `suggest_outfit()` tool and use the `load_wardrobe_schema()` from the data loader. I'll also ask Claude to generate tests for both the example wardrobe and an empty wardrobe with `get_example_wardrobe()` and `get_empty_wardrobe()` from the data loader.

I'll give Claude the Tool 3 spec to implement `create_fit_card()` tool. I'll ask Claude to generate tests for a real outfit string and an empty outfit.


**Milestone 4 — Planning loop and state management:**

I'll give Claude my Planning Loop section, the `session` dict from State Management, and the Architecture diagram, and ask it to implement `run_agent()` in `agent.py`. I'll ask Claude to generate tests for the my "Complete Interaction" example, which is a good example that should go through the whole loop, and a no-match query to test error setting and stopping the loop early.


---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"


**Step 1:**

The agent needs to first find a vintage graphic tee under $30 in its listings. It will call `search_listings` tool and use the price as an input, so the tool calling should be `search_listings("vintage graphic tee", max_price=30).


**Step 2:**

The tool calling should return the top 3 matching results from its listings sorted by relevance, where the agent mirrors into `session["search_results"]`. 

If no match is found, the agent sets error, ends the interaction early, and returns "no results found" message.

Otherwise, the agent should set the selected item as `search_results[0]` (the top relevant result). The model calls `suggest_outfit(new_item=<band tee>, wardrobe=<user's wardrobe>` tool to help user with styling. The result will be mirrored in `session["outfit_suggestion"]`.


**Step 3:**
The model calls `create_fit_card(outfit=<suggestion>, new_item=<band tee>)` and stores the results in `session["fit_card"]`. Since the model has all three results, LLM replies with plain text (no tool calls), the loop ends and returns the session.


**Final output to user:**
The user should see the matched listing under the "Top listing found", the styling suggestion string under "Outfit idea", and the shareable fit card caption for SMS posts under "Your fit card" on the interface.