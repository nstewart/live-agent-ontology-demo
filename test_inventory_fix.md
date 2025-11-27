# Inventory Validation Fixes

## Problem
The agent was claiming items were available when they weren't actually in stock.

Example: For chicken burrito, agent claimed these were all available at BK-01:
- ✅ Chicken Breast (actually available)
- ❌ Tortillas (NOT in inventory)
- ❌ Cheese (NOT in inventory)
- ❌ Beans (NOT in inventory)
- ❌ Rice (NOT in inventory)
- ❌ Salsa (NOT in inventory)

## Root Causes

### 1. search_inventory tool (tool_search_inventory.py)
**Before:**
- Only returned product IDs like "product:milk-1L" without names
- Did simple string matching on product_id only
- **Returned ALL inventory items** when query didn't match anything
- Had comment "Product details lookup not yet implemented"

**Result:** Agent saw mysterious product IDs, hallucinated the names

### 2. create_order tool (tool_create_order.py)
**Before:**
- No validation that items actually exist in store inventory
- Would create orders with ANY product_id
- Relied on agent to use search_inventory (which it didn't)

## Solutions Implemented

### 1. Fixed search_inventory tool
**Now:**
- Fetches actual product names from API via `/triples/subjects/{product_id}`
- Returns complete product info: name, category, price, perishability
- **Only returns products matching the search query**
- Searches across product name, category, AND product_id
- No more "return everything" fallback

**Example output:**
```json
[
  {
    "product_id": "product:chicken-breast",
    "product_name": "Chicken Breast 1lb",
    "category": "Meat",
    "unit_price": 8.99,
    "quantity_available": 25,
    "is_perishable": true
  }
]
```

### 2. Fixed create_order tool
**Now:**
- Validates ALL items against OpenSearch inventory before creating order
- **Automatically filters** out items not in store inventory
- **Adjusts quantities** when stock is insufficient
- Returns detailed feedback about what was skipped/adjusted
- **Only errors** when NO items are available

**Validation flow:**
```
Requested items → Check inventory → Filter/adjust → Create order with valid items only
```

## What This Means

### For search_inventory:
Search "tortillas" at BK-01 → Returns empty list (not in stock)
Search "chicken" at BK-01 → Returns "Chicken Breast 1lb" with full details

### For create_order:
Request: [milk (in stock), tortillas (not in stock)]
Result: Order created with milk only
        skipped_items: [{"product_id": "product:tortillas", "reason": "not available at this store"}]

Request: [tortillas, salsa, beans] (none in stock)
Result: ERROR with list of what IS available

## Actual BK-01 Inventory
- Organic Whole Milk 1L (45 units)
- Free Range Eggs 12-pack (30 units)
- Artisan Sourdough Loaf (15 units)
- Chicken Breast 1lb (25 units)
- Gala Apples 6-pack (100 units)

**That's it!** No tortillas, cheese, beans, rice, or salsa.

## Testing
Run: `python -m pytest tests/test_tools.py::TestCreateOrder -v`

New test coverage:
- test_filters_unavailable_items
- test_adjusts_quantity_for_insufficient_stock
- test_returns_error_when_no_items_available
