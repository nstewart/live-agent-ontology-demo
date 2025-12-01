# Admin UI Guide

Complete guide to the FreshMart Admin UI with real-time updates and comprehensive entity management.

## Table of Contents

- [Overview](#overview)
- [Real-Time Updates](#real-time-updates)
- [Orders Dashboard](#orders-dashboard)
- [Couriers & Schedule](#couriers--schedule)
- [Stores & Inventory](#stores--inventory)
- [Ontology Properties](#ontology-properties)
- [Triples Browser](#triples-browser)

## Overview

The React Admin UI (`web/`) provides full CRUD operations with **real-time updates** for managing FreshMart entities.

**Access**: http://localhost:5173

**Key Features**:
- Real-time WebSocket synchronization
- Visual connection status indicator
- Instant updates across all connected clients
- Ontology-powered dynamic forms
- Entity relationship navigation

## Real-Time Updates

All operational dashboards (Orders, Couriers, Stores/Inventory) feature **live data synchronization**:

### WebSocket Connection

- **Direct connection** to Zero server at `ws://localhost:8090`
- **Connection indicator**: Visual badge showing real-time connection status
  - Green: Connected and receiving updates
  - Yellow: Connecting/Reconnecting
  - Red: Disconnected
- **Instant updates**: Changes from any source (UI, API, database) appear immediately
- **Differential updates**: Only changed data is transmitted, minimizing bandwidth
- **Automatic reconnection**: Handles network interruptions gracefully

### How It Works

```
User Action → API → PostgreSQL → CDC → Materialize → Zero Server → WebSocket → UI
                                                                    (< 1 second)
```

**Example Flow**:
1. User updates order status in UI
2. API writes triple to PostgreSQL
3. CDC streams change to Materialize
4. Materialize updates materialized view
5. Zero server detects change via SUBSCRIBE
6. WebSocket broadcasts to all connected clients
7. UI automatically re-renders with new data

### Benefits

- **No polling**: Efficient real-time updates without constant API requests
- **Multi-user collaboration**: All users see changes instantly
- **Consistency**: Single source of truth (PostgreSQL) propagated everywhere
- **Responsive UX**: Immediate feedback on all operations

## Orders Dashboard

Comprehensive order management with real-time status updates and dynamic pricing.

### Features

- **Real-time order status updates**: See orders move through workflow stages instantly
- **Live dynamic pricing**: Product prices update in real-time based on zone, stock, and demand
- View all orders with status badges and filtering
- Create new orders with dropdown selectors
- Edit existing orders
- Delete orders with confirmation

### View Orders

**Displays**:
- Order number and ID
- Current status (CREATED, PICKING, OUT_FOR_DELIVERY, DELIVERED, CANCELLED)
- Customer name and address
- Store location
- Delivery window
- Order total (with dynamic pricing)
- Line items with quantities and prices

**Filters**:
- By order status
- By store
- By customer
- Search by order number

### Create Order

1. Click "Create Order" button
2. Select customer from dropdown (populated from `customers_mv`)
3. Select store from dropdown (populated from `stores_mv`)
4. Add products to shopping cart:
   - Search/select products
   - Specify quantities
   - See live prices (not base prices!)
5. Set delivery window (optional)
6. Review order total (calculated from live prices)
7. Submit

**Features**:
- Products dropdown shows inventory with stock levels
- Live dynamic pricing based on zone, demand, and stock
- Shopping cart calculates totals using current prices
- Stock validation before order creation
- Automatic order number generation

### Edit Order

1. Click "Edit" on any order
2. Update customer, store, or line items
3. Modify delivery window
4. Save changes

**Note**: Form pre-populates with current values

### Delete Order

1. Click "Delete" on any order
2. Confirm in dialog
3. Order and all line items removed

## Couriers & Schedule

Manage delivery personnel and view real-time task assignments.

### Features

- **Real-time courier availability**: Status updates appear instantly
- **Live task assignments**: See deliveries assigned in real-time
- View all couriers with assigned tasks
- Create new couriers
- Edit courier details
- Delete couriers

### View Couriers

**Displays**:
- Courier name and ID
- Current status (AVAILABLE, BUSY, OFF_DUTY)
- Phone number
- Home store
- Vehicle type
- Schedule (start/end times)
- Assigned delivery tasks with:
  - Order ID
  - Task status
  - ETA

**Filters**:
- By status
- By home store

### Create Courier

1. Click "Create Courier" button
2. Enter courier name
3. Enter phone number
4. Select home store from dropdown
5. Select vehicle type
6. Set schedule times
7. Set initial status
8. Submit

### Edit Courier

1. Click "Edit" on any courier
2. Update name, phone, or vehicle
3. Change status or schedule
4. Save changes

### Delete Courier

1. Click "Delete" on any courier
2. Confirm in dialog
3. Courier removed from system

## Stores & Inventory

Manage store locations and inventory levels with real-time synchronization.

### Features

- **Real-time inventory updates**: Stock changes appear instantly
- View stores with current inventory levels
- Create/edit stores
- Manage inventory items per store
- Expandable inventory view

### View Stores

**Displays**:
- Store name and ID
- Zone (Manhattan, Brooklyn, Queens, Bronx, Staten Island)
- Address
- Capacity
- Inventory items:
  - Product name
  - Stock level
  - Price
  - Perishable indicator

**Note**: Inventory items sorted by inventory ID for stability

### Create Store

1. Click "Create Store" button
2. Enter store name
3. Enter address
4. Select zone
5. Set capacity
6. Submit

### Edit Store

1. Click "Edit" on any store
2. Update name, address, zone, or capacity
3. Save changes

### Manage Inventory

Each store has expandable inventory section:

**View Inventory**:
- Expand store row to see all inventory items
- Shows product details and stock levels

**Add Inventory**:
1. Click "Add Inventory" for a store
2. Select product from dropdown
3. Enter stock level
4. Set price
5. Submit

**Edit Inventory**:
1. Click "Edit" on any inventory item
2. Update stock level or price
3. Save changes

**Delete Inventory**:
1. Click "Delete" on any inventory item
2. Confirm in dialog
3. Inventory item removed

## Ontology Properties

Manage ontology schema with dynamic property definitions.

### Features

- View all ontology properties
- Filter by domain class
- Create new properties
- Edit existing properties
- Delete properties

### View Properties

**Displays**:
- Property name
- Domain class (which entity type it applies to)
- Range kind (data type: string, integer, float, bool, timestamp, entity_ref)
- Range class (for entity_ref types)
- Required flag
- Description

**Grouped by domain class** for easy navigation

### Create Property

1. Click "Add Property" for a class
2. Enter property name
3. Select **Domain Class** from dropdown (which entity type)
4. Select **Range Kind**:
   - `string` - Text values
   - `integer` - Whole numbers
   - `float` - Decimal numbers
   - `bool` - Boolean (true/false)
   - `timestamp` - Date/time values
   - `entity_ref` - Reference to another entity
5. If entity_ref, select **Range Class** (target entity type)
6. Set required flag
7. Enter description
8. Submit

**Dropdowns populated from ontology**:
- Domain classes from `ontology_classes`
- Range classes from `ontology_classes`

### Edit Property

1. Click "Edit" on any property
2. Update description or required flag
3. Save changes

**Note**: Cannot change property name, domain, or range after creation

### Delete Property

1. Click "Delete" on any property
2. Confirm in dialog
3. Property removed from ontology

**Warning**: Deleting a property may break existing triples

## Triples Browser

Advanced interface for exploring and managing the knowledge graph.

### Features

- Browse all entities with filtering
- View entity details with all triples
- Create triples with ontology-powered forms
- Edit triple values
- Delete triples or entire entities
- Navigate entity relationships

### Browse Entities

**Filter by entity type**:
- Select class prefix (customer:, order:, store:, etc.)
- View all entities of that type
- Click to expand and see all triples

**Display shows**:
- Subject ID
- Count of triples
- Last updated timestamp

### View Entity Details

Click on any entity to see all associated triples:

**Displays**:
- Subject ID
- Predicate (property name)
- Object value
- Object type
- Timestamps (created, updated)

**Navigate relationships**:
- Click on entity_ref values to navigate to related entities
- Example: Click "store:BK-01" in an order to view store details

### Create Triple

1. Click "Create Triple" button
2. **Subject ID**:
   - Select class prefix from dropdown (customer:, order:, store:, etc.)
   - Enter entity ID
3. **Predicate**:
   - Dropdown filtered by subject's class (from ontology)
   - Shows only valid properties for that entity type
4. **Value**:
   - Input type adapts to range_kind:
     - String/Integer/Float: Text input
     - Boolean: Checkbox
     - Timestamp: DateTime picker
     - Entity reference: Dropdown (populated from target class)
5. Submit

**Validation**:
- Ontology validates subject prefix matches class
- Predicate must be defined for subject's class
- Value type must match range_kind
- Entity references must point to existing entities

### Edit Triple

1. Click "Edit" on any triple
2. Update object value
3. Input type matches data type
4. Save changes

**Note**: Cannot change subject or predicate, only value

### Delete Triple

**Delete Single Triple**:
1. Click "Delete" on any triple
2. Confirm in dialog
3. Triple removed

**Delete All Triples for Entity**:
1. Click "Delete Entity" button
2. Confirm in dialog
3. All triples for that subject removed

**Warning**: Deleting entity may break relationships

## Data Synchronization

All UI updates trigger the following flow:

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. UI Action (Create/Update/Delete)                             │
│    → React component calls API                                  │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. API Writes to PostgreSQL                                     │
│    → Validates against ontology                                 │
│    → Inserts/updates triples table                              │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ (< 100ms)
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. CDC Streams to Materialize                                   │
│    → Change Data Capture replicates change                      │
│    → Materialized views update                                  │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ (< 200ms)
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Zero Server Broadcasts                                       │
│    → SUBSCRIBE detects view change                              │
│    → Sends differential update via WebSocket                    │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ (< 100ms)
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. UI Auto-Updates                                              │
│    → React component receives update                            │
│    → Re-renders with new data                                   │
│    → All connected clients see change                           │
└─────────────────────────────────────────────────────────────────┘

Total latency: < 500ms (action → all UIs updated)
```

## Technical Details

### Technology Stack

- **React** with Vite for fast development
- **Zero (@rocicorp/zero)** for real-time WebSocket sync
- **TanStack Query** for non-real-time API calls
- **Tailwind CSS** for styling
- **TypeScript** for type safety

### Zero Integration

```typescript
// Zero client setup (web/src/zero.ts)
const zero = new Zero({
  userID: 'anon',
  server: 'ws://localhost:8090',
  schema,
})

// Subscribe to view with filters
const [orders] = useQuery(
  z.query.orders_flat_mv
    .where("order_status", "=", "PICKING")
    .where("store_id", "=", "store:BK-01")
    .orderBy("order_number", "asc")
);
// orders automatically updates when data changes
```

### Supported Filters

Zero queries support SQL-compatible filtering:
- `=`, `!=` - Equality
- `<`, `>`, `<=`, `>=` - Comparison
- `LIKE`, `ILIKE` - Pattern matching
- `IN` - Multiple values
- `IS`, `IS NOT` - NULL checks

### Performance

- **Initial load**: < 1 second (hydration from materialized views)
- **Update latency**: < 500ms (write → all UIs)
- **Bandwidth**: Minimal (differential updates only)
- **Scalability**: Supports hundreds of concurrent users

## See Also

- [Architecture Guide](ARCHITECTURE.md) - Real-time data flow details
- [API Reference](API_REFERENCE.md) - API endpoints used by UI
- [Operations Guide](OPERATIONS.md) - Service management
- [Dynamic Pricing Guide](DYNAMIC_PRICING.md) - Live pricing feature
