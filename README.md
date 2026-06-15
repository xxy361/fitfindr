# FitFindr

FitFindr is an AI styling agent: give it a natural-language request for a
secondhand item plus your wardrobe, and it finds a matching listing, styles it
against pieces you already own, and writes a shareable caption for the find.

## What's Included

```
fitfindr/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── tests/
│   ├── test_tools.py          # Unit tests for the tools
│   ├── test_agent.py          # End-to-end planning-loop / state-flow tests
│   └── test_edge_cases.py     # Failure-mode tests
├── tools.py                   # The tools 
├── agent.py                   # The planning loop that orchestrates the tools
├── app.py                     # Gradio interface
├── config.py                  # Loads GROQ_API_KEY and LLM_MODEL from .env
├── planning.md                # Planning doc — completed before implementation
└── requirements.txt           # Python dependencies
```

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.

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


### Additional Tools (if any)

TBD



## Planning Loop

**How does your agent decide which tool to call next?**

When a session starts, the loop sends the user query plus all three tool schemas to the LLM, and a `session` dict tracks state. Each turn the model decides the tool call while the loop checks the result: 
1. after `search_listings`, if `search_results == []` it sets `session["error"]` and returns early (never calling `suggest_outfit` with no item), otherwise it sets `selected_item = search_results[0]` and re-invokes
2. after `suggest_outfit` it always stores `outfit_suggestion` (if empty wardrobe, returns general advice, no error and continue)
3. after `create_fit_card` it always stores `fit_card` (returns fallback string, no error and continue). 

Before each call the loop checks a `max_steps` cap and sets `error` if exceeded. The loop ends successfully when the model returns plain text with no `tool_calls`, or early when error is set or max steps is reached.


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

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Stops the loop and sets `session["error"]`, returns message to user: "Hmm, I couldn't find anything matching that right now. 😕 Try loosening the size or price filters, or describing the item differently." |
| suggest_outfit | Wardrobe is empty | Does not stop the loop or set error. The tool would give general outfit advice on the new item: "Looks like your wardrobe is empty here, so here's how I'd style this piece from scratch: pair it with <neutral basics / contrasting textures> and it'd give off a <vibe> look. 😎 " The loop continues. |
| create_fit_card | Outfit input is missing or incomplete | Returns a fallback string and does not set error: "I couldn't whip up a caption without an outfit to work from — let's find you a piece first and I'll make it shareable! ✨" |


**Concrete example from testing:** 

Use the test file `python -m pytest tests/test_edge_cases.py -v -s`.

1. Trigger `search_listings` returning zero results.

    `print(search_listings('designer ballgown', size='XXS', max_price=5))`

    Output:
    ```
    []
    ```

    `print(run_agent('designer ballgown size XXS under $5', get_example_wardrobe())["error"])`

    Output:
    ```
    Hmm, I couldn't find anything matching that right now. 😕 Try loosening the size or price filters, or describing the item differently.
    ```




2. Trigger `suggest_outfit` with an empty wardrobe:

    `results = search_listings('vintage graphic tee', size=None, max_price=50)`
    `print(suggest_outfit(results[0], get_empty_wardrobe()))`
    
    Output:

    ```
    Looks like your wardrobe is empty here, so here's how I'd style this piece from scratch: This adorable Y2K baby tee pairs perfectly with high-waisted jeans or a flowy skirt for a nostalgic and playful vibe. To build a look, consider adding some distressed denim, a pair of chunky sneakers, or a floppy hat to enhance the vintage feel, and balance out the sweetness of the butterfly graphic. You can also layer a cardigan or a denim jacket over the tee for a more laid-back, cottagecore-inspired look. 😎
    ```

3. Trigger `create_fit_card` with an empty outfit string:

    `results = search_listings('vintage graphic tee', size=None, max_price=50)`
    `print(create_fit_card('', results[0]))`

    Output:

    ```
    I couldn't whip up a caption without an outfit to work from — let's find you a piece first and I'll make it shareable! ✨
    ```


## Complete Interaction (End-to-End Walkthrough)

A full run of `run_agent(query, wardrobe)` for the query
"I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"


**Step 1:**

The agent needs to first find a vintage graphic tee under $30 in its listings. It will call `search_listings` tool and use the price as an input and the rest of the string as description.


**Step 2:**

The tool calling should return the top 3 matching results from its listings sorted by relevance, where the agent mirrors into `session["search_results"]`. 

If no match is found, the agent sets error, ends the interaction early, and returns "no results found" message.

Otherwise, the agent should set the selected item as `search_results[0]` (the top relevant result). The model calls `suggest_outfit(new_item=<band tee>, wardrobe=<user's wardrobe>` tool to help user with styling. The result will be mirrored in `session["outfit_suggestion"]`.


**Step 3:**
The model calls `create_fit_card(outfit=<suggestion>, new_item=<band tee>)` and stores the results in `session["fit_card"]`. Since the model has all three results, LLM replies with plain text (no tool calls), the loop ends and returns the session.


**Final output to user:**
The user should see the matched listing under the "Top listing found", the styling suggestion string under "Outfit idea", and the shareable fit card caption for SMS posts under "Your fit card" on the interface.


**Test Transcript**

Use the test file and print all values: `python -m pytest tests/test_agent.py -v -s`

```
tests/test_agent.py::test_state_flows_by_reference 
======================================================================
RUN AGENT  query="I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"
======================================================================

======================================================================
TOOL CALL: search_listings
======================================================================
  INPUT  description="I'm looking for a vintage graphic tee . I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?" size=None max_price=30.0
  OUTPUT 3 listing(s):
    [0] id='lst_006'      title='Graphic Tee — 2003 Tour Bootleg Style' $24
    [1] id='lst_002'      title='Y2K Baby Tee — Butterfly Print' $18
    [2] id='lst_017'      title='Mesh Long-Sleeve Top — Black' $15

======================================================================
TOOL CALL: suggest_outfit
======================================================================
  INPUT  new_item id='lst_006' title='Graphic Tee — 2003 Tour Bootleg Style'
         new_item object id = 2331200967616
         wardrobe items: 10
  OUTPUT outfit_suggestion (object id = 2331146382272):
    I'm excited to help you style your new Graphic Tee. Here are two complete outfit ideas that pair perfectly with pieces you already own:

**Outfit 1: Grunge Revival**
Pair your Graphic Tee with the Baggy straight-leg jeans, dark wash, and Black combat boots. Add a touch of edge with the Vintage black denim jacket. This outfit screams 90s grunge, and the faded graphic on your tee will look rad with the high-waisted, baggy jeans. 
Styling note: Keep your hair messy and undone to complete the look.

**Outfit 2: Streetwear Chic**
Combine your Graphic Tee with the Wide-leg khaki trousers and Chunky white sneakers. Throw on the Black cropped zip hoodie for a sporty touch. This outfit blends streetwear with a hint of earthy tones, and the contrast between the black tee and khaki trousers will create a cool, laid-back vibe.
Styling note: Accessorize with the Brown leather belt to add a pop of warmth to your overall look.

Both outfits will make your new Graphic Tee shine, and you can always mix and match pieces to create more unique combinations. Have fun and rock your new tee!

======================================================================
TOOL CALL: create_fit_card
======================================================================
  INPUT  outfit (object id = 2331146382272):
    I'm excited to help you style your new Graphic Tee. Here are two complete outfit ideas that pair perfectly with pieces you already own:

**Outfit 1: Grunge Revival**
Pair your Graphic Tee with the Baggy straight-leg jeans, dark wash, and Black combat boots. Add a touch of edge with the Vintage black denim jacket. This outfit screams 90s grunge, and the faded graphic on your tee will look rad with the high-waisted, baggy jeans. 
Styling note: Keep your hair messy and undone to complete the look.

**Outfit 2: Streetwear Chic**
Combine your Graphic Tee with the Wide-leg khaki trousers and Chunky white sneakers. Throw on the Black cropped zip hoodie for a sporty touch. This outfit blends streetwear with a hint of earthy tones, and the contrast between the black tee and khaki trousers will create a cool, laid-back vibe.
Styling note: Accessorize with the Brown leather belt to add a pop of warmth to your overall look.

Both outfits will make your new Graphic Tee shine, and you can always mix and match pieces to create more unique combinations. Have fun and rock your new tee!
  INPUT  new_item id='lst_006' (object id = 2331200967616)
  OUTPUT fit_card:
    "Just scored the Graphic Tee — 2003 Tour Bootleg Style for $24 on depop and I'm obsessed 🤩! I paired it with my fave baggy straight-leg jeans, black combat boots, and vintage black denim jacket for a grunge revival vibe - think 90s nostalgia with a rad, edgy twist. The tee looks rad with the high-waisted, baggy jeans and adds a cool touch to my everyday look 😎"

======================================================================
FINAL SESSION STATE
======================================================================
  parsed            : {'description': "I'm looking for a vintage graphic tee . I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?", 'size': None, 'max_price': 30.0}
  selected_item     : (object id = 2331200967616)
    {'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}
  outfit_suggestion : (object id = 2331146382272)
    I'm excited to help you style your new Graphic Tee. Here are two complete outfit ideas that pair perfectly with pieces you already own:

**Outfit 1: Grunge Revival**
Pair your Graphic Tee with the Baggy straight-leg jeans, dark wash, and Black combat boots. Add a touch of edge with the Vintage black denim jacket. This outfit screams 90s grunge, and the faded graphic on your tee will look rad with the high-waisted, baggy jeans. 
Styling note: Keep your hair messy and undone to complete the look.

**Outfit 2: Streetwear Chic**
Combine your Graphic Tee with the Wide-leg khaki trousers and Chunky white sneakers. Throw on the Black cropped zip hoodie for a sporty touch. This outfit blends streetwear with a hint of earthy tones, and the contrast between the black tee and khaki trousers will create a cool, laid-back vibe.
Styling note: Accessorize with the Brown leather belt to add a pop of warmth to your overall look.

Both outfits will make your new Graphic Tee shine, and you can always mix and match pieces to create more unique combinations. Have fun and rock your new tee!
  fit_card          : "Just scored the Graphic Tee — 2003 Tour Bootleg Style for $24 on depop and I'm obsessed 🤩! I paired it with my fave baggy straight-leg jeans, black combat boots, and vintage black denim jacket for a grunge revival vibe - think 90s nostalgia with a rad, edgy twist. The tee looks rad with the high-waisted, baggy jeans and adds a cool touch to my everyday look 😎"
  error             : None

======================================================================
STATE-FLOW IDENTITY CHECKS  (is, not ==)
======================================================================
  [PASS] selected_item IS search_results[0] (top result, not hardcoded)
  [PASS] selected_item IS the dict passed into suggest_outfit
  [PASS] suggest_outfit's return IS session['outfit_suggestion']
  [PASS] outfit_suggestion IS the string passed into create_fit_card
  [PASS] selected_item IS the dict passed into create_fit_card
======================================================================
PASSED
```

---

## Spec Reflection

**One way the spec helped:** 
Writing out the `session` dict fields and the tool input/output in `planning.md` was very helpful for implementation. When using AI for implementation, it obviously gives AI a fixed shape to fill, and without reading the files where those structures are implemented. But it was also helpful for human to review and avoiding going back and forth looking through files.

**One divergence and why:** 
The plan (Step 1 in Walkthrough) was to extract a clean phrase (`search_listings("vintage graphic tee", max_price=30)`), but the actual implementation only strips size and price and passes the rest of the query through as the `description`. Though, this still finds the right tee because it scores by keyword overlap. The tradeoff of using regex stripping is that it is deterministic and not perfect, but it is cheap since extracting the exact item phrase would need an another LLM call.



## AI Usage Transparency

**Instance 1 — Implement Agent.py:**
I gave Claude my Planning Loop section, the `session` dict from State Management, and the Architecture diagram, and ask it to implement `run_agent()` in `agent.py`. Claude invented an error messgae for empty listings search as I didn't pass it the Error Handling section. I passed the exact error message to Claude and reviewed that all the error messages matched my plan.

**Instance 2 — System Prompt:**
I gave Claude the Tool 2 spec to implement `suggest_outfit()` tool and use the `load_wardrobe_schema()` from the data loader. Claude was able to implement the function, including the system and user prompts for LLM calls. However, it assumed FitFindr was a "thrifted-fashion stylist", which I told it to revise that FitFindr is for general, not thrifted fashion.
