# API Reference

Complete API documentation for the FreshMart Digital Twin Graph/Ontology API.

## Table of Contents

- [Overview](#overview)
- [Ontology Management](#ontology-management)
- [Triple Store CRUD](#triple-store-crud)
- [FreshMart Operations](#freshmart-operations)
- [Health and Monitoring](#health--monitoring)
- [Security Features](#security-features)

## Overview

The Graph API (FastAPI, Port 8080) provides three main categories of endpoints:

1. **Ontology Management** (`/ontology`) - Define and manage schema
2. **Triple Store CRUD** (`/triples`) - Manage knowledge graph data
3. **FreshMart Operations** (`/freshmart`) - Query operational views

**Base URL**: `http://localhost:8080`

**Interactive Docs**: Visit `http://localhost:8080/docs` for Swagger UI

## Ontology Management

Endpoints for defining and managing the knowledge graph schema (classes and properties).

### Classes

#### List All Classes

```http
GET /ontology/classes
```

**Response:**
```json
[
  {
    "id": 1,
    "class_name": "Customer",
    "prefix": "customer",
    "description": "People who place orders",
    "parent_class_id": null
  }
]
```

#### Get Specific Class

```http
GET /ontology/classes/{id}
```

**Parameters:**
- `id` (integer): Class ID

**Response:**
```json
{
  "id": 1,
  "class_name": "Customer",
  "prefix": "customer",
  "description": "People who place orders",
  "parent_class_id": null
}
```

#### Create Class

```http
POST /ontology/classes
```

**Request Body:**
```json
{
  "class_name": "Promotion",
  "prefix": "promo",
  "description": "Marketing promotions and discounts"
}
```

**Response:**
```json
{
  "id": 10,
  "class_name": "Promotion",
  "prefix": "promo",
  "description": "Marketing promotions and discounts",
  "parent_class_id": null
}
```

#### Update Class

```http
PATCH /ontology/classes/{id}
```

**Request Body:**
```json
{
  "description": "Updated description for marketing promotions"
}
```

#### Delete Class

```http
DELETE /ontology/classes/{id}
```

**Response:** 204 No Content

#### Get Class Properties

```http
GET /ontology/class/{class_name}/properties
```

**Parameters:**
- `class_name` (string): Name of the class (e.g., "Order")

**Response:**
```json
[
  {
    "id": 15,
    "prop_name": "order_number",
    "domain_class_id": 3,
    "range_kind": "string",
    "range_class_id": null,
    "is_required": true,
    "description": "Unique order number"
  }
]
```

### Properties

#### List All Properties

```http
GET /ontology/properties
```

**Query Parameters:**
- `domain_class_id` (optional, integer): Filter by domain class

**Response:**
```json
[
  {
    "id": 15,
    "prop_name": "order_number",
    "domain_class_id": 3,
    "domain_class_name": "Order",
    "range_kind": "string",
    "range_class_id": null,
    "is_required": true,
    "description": "Unique order number"
  }
]
```

#### Get Specific Property

```http
GET /ontology/properties/{id}
```

**Response:**
```json
{
  "id": 15,
  "prop_name": "order_number",
  "domain_class_id": 3,
  "range_kind": "string",
  "range_class_id": null,
  "is_required": true,
  "description": "Unique order number"
}
```

#### Create Property

```http
POST /ontology/properties
```

**Request Body (String Property):**
```json
{
  "prop_name": "promo_code",
  "domain_class_id": 10,
  "range_kind": "string",
  "is_required": true,
  "description": "Unique promotion code"
}
```

**Request Body (Entity Reference):**
```json
{
  "prop_name": "promo_applied",
  "domain_class_id": 3,
  "range_kind": "entity_ref",
  "range_class_id": 10,
  "is_required": false,
  "description": "Promotion applied to this order"
}
```

**Range Kinds:**
- `string` - Text values
- `integer` - Whole numbers
- `float` - Decimal numbers
- `bool` - Boolean (true/false)
- `timestamp` - Date/time values
- `entity_ref` - Reference to another entity (requires `range_class_id`)

#### Update Property

```http
PATCH /ontology/properties/{id}
```

**Request Body:**
```json
{
  "description": "Updated property description",
  "is_required": false
}
```

#### Delete Property

```http
DELETE /ontology/properties/{id}
```

**Response:** 204 No Content

#### Get Complete Schema

```http
GET /ontology/schema
```

**Response:**
```json
{
  "classes": [...],
  "properties": [...]
}
```

## Triple Store CRUD

Endpoints for managing knowledge graph data as subject-predicate-object triples.

### Triple Operations

#### List Triples

```http
GET /triples
```

**Query Parameters:**
- `subject_id` (optional, string): Filter by subject
- `predicate` (optional, string): Filter by predicate
- `object_value` (optional, string): Filter by object value
- `object_type` (optional, string): Filter by object type
- `limit` (optional, integer, default: 100): Max results
- `offset` (optional, integer, default: 0): Pagination offset

**Response:**
```json
[
  {
    "id": 1001,
    "subject_id": "order:FM-1001",
    "predicate": "order_status",
    "object_value": "DELIVERED",
    "object_type": "string",
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T14:20:00Z"
  }
]
```

#### Get Specific Triple

```http
GET /triples/{id}
```

**Response:**
```json
{
  "id": 1001,
  "subject_id": "order:FM-1001",
  "predicate": "order_status",
  "object_value": "DELIVERED",
  "object_type": "string"
}
```

#### Create Triple

```http
POST /triples
```

**Query Parameters:**
- `validate` (optional, boolean, default: true): Validate against ontology

**Request Body:**
```json
{
  "subject_id": "order:FM-1001",
  "predicate": "order_status",
  "object_value": "OUT_FOR_DELIVERY",
  "object_type": "string"
}
```

**Response:**
```json
{
  "id": 1002,
  "subject_id": "order:FM-1001",
  "predicate": "order_status",
  "object_value": "OUT_FOR_DELIVERY",
  "object_type": "string"
}
```

**Validation Errors:**
```json
{
  "detail": "Property 'invalid_prop' not defined in ontology for class 'Order'"
}
```

#### Bulk Create Triples

```http
POST /triples/batch
```

**Request Body:**
```json
[
  {
    "subject_id": "promo:SUMMER25",
    "predicate": "promo_code",
    "object_value": "SUMMER25",
    "object_type": "string"
  },
  {
    "subject_id": "promo:SUMMER25",
    "predicate": "discount_percent",
    "object_value": "15.0",
    "object_type": "float"
  }
]
```

**Response:**
```json
[
  {"id": 1003, "subject_id": "promo:SUMMER25", ...},
  {"id": 1004, "subject_id": "promo:SUMMER25", ...}
]
```

#### Update Triple

```http
PATCH /triples/{id}
```

**Request Body:**
```json
{
  "object_value": "DELIVERED"
}
```

**Response:**
```json
{
  "id": 1001,
  "subject_id": "order:FM-1001",
  "predicate": "order_status",
  "object_value": "DELIVERED",
  "object_type": "string"
}
```

#### Delete Triple

```http
DELETE /triples/{id}
```

**Response:** 204 No Content

#### Validate Triple

Validate a triple without creating it:

```http
POST /triples/validate
```

**Request Body:**
```json
{
  "subject_id": "order:FM-NEW",
  "predicate": "order_status",
  "object_value": "CREATED",
  "object_type": "string"
}
```

**Response (Valid):**
```json
{
  "is_valid": true,
  "errors": []
}
```

**Response (Invalid):**
```json
{
  "is_valid": false,
  "errors": [
    "Property 'invalid_status' not defined for class 'Order'"
  ]
}
```

### Subject Operations

#### List Distinct Subjects

```http
GET /triples/subjects/list
```

**Query Parameters:**
- `class_name` (optional, string): Filter by class name
- `prefix` (optional, string): Filter by prefix

**Response:**
```json
[
  "order:FM-1001",
  "order:FM-1002",
  "order:FM-1003"
]
```

#### Get Entity Counts by Type

```http
GET /triples/subjects/counts
```

**Response:**
```json
{
  "customer": 150,
  "order": 500,
  "store": 5,
  "product": 200
}
```

#### Get All Triples for Entity

```http
GET /triples/subjects/{subject_id}
```

**Example:**
```http
GET /triples/subjects/order:FM-1001
```

**Response:**
```json
[
  {
    "id": 1001,
    "subject_id": "order:FM-1001",
    "predicate": "order_number",
    "object_value": "FM-1001",
    "object_type": "string"
  },
  {
    "id": 1002,
    "subject_id": "order:FM-1001",
    "predicate": "order_status",
    "object_value": "DELIVERED",
    "object_type": "string"
  }
]
```

#### Delete All Triples for Entity

```http
DELETE /triples/subjects/{subject_id}
```

**Example:**
```http
DELETE /triples/subjects/order:FM-1001
```

**Response:**
```json
{
  "deleted_count": 15
}
```

## FreshMart Operations

Query pre-computed, denormalized views (powered by Materialize).

### Orders

#### List Orders

```http
GET /freshmart/orders
```

**Query Parameters:**
- `status` (optional, string): Filter by order status (CREATED, PICKING, OUT_FOR_DELIVERY, DELIVERED, CANCELLED)
- `store_id` (optional, string): Filter by store ID (e.g., "store:BK-01")
- `customer_id` (optional, string): Filter by customer ID
- `window_start_before` (optional, datetime): Orders with delivery window starting before
- `window_end_after` (optional, datetime): Orders with delivery window ending after
- `limit` (optional, integer, default: 100)
- `offset` (optional, integer, default: 0)

**Response:**
```json
[
  {
    "order_id": "order:FM-1001",
    "order_number": "FM-1001",
    "order_status": "DELIVERED",
    "store_id": "store:BK-01",
    "store_name": "FreshMart Brooklyn 1",
    "customer_id": "customer:123",
    "customer_name": "Alex Thompson",
    "customer_email": "alex@example.com",
    "delivery_window_start": "2025-01-15T14:00:00Z",
    "delivery_window_end": "2025-01-15T16:00:00Z",
    "order_total_amount": 125.50,
    "line_items": [
      {
        "product_id": "product:MILK-WH",
        "product_name": "Whole Milk Gallon",
        "quantity": 2,
        "unit_price": 4.99,
        "line_amount": 9.98
      }
    ]
  }
]
```

#### Get Order Details

```http
GET /freshmart/orders/{order_id}
```

**Example:**
```http
GET /freshmart/orders/order:FM-1001
```

**Response:**
```json
{
  "order_id": "order:FM-1001",
  "order_number": "FM-1001",
  "order_status": "DELIVERED",
  "store_id": "store:BK-01",
  "store_name": "FreshMart Brooklyn 1",
  "customer_id": "customer:123",
  "customer_name": "Alex Thompson",
  "customer_email": "alex@example.com",
  "customer_address": "123 Main St, Brooklyn",
  "delivery_window_start": "2025-01-15T14:00:00Z",
  "delivery_window_end": "2025-01-15T16:00:00Z",
  "order_total_amount": 125.50,
  "assigned_courier_id": "courier:C01",
  "delivery_task_status": "COMPLETED",
  "delivery_eta": "2025-01-15T15:30:00Z",
  "line_items": [...]
}
```

### Stores & Inventory

#### List Stores

```http
GET /freshmart/stores
```

**Response:**
```json
[
  {
    "store_id": "store:BK-01",
    "store_name": "FreshMart Brooklyn 1",
    "store_zone": "Brooklyn",
    "store_address": "456 Atlantic Ave, Brooklyn",
    "store_capacity": 100,
    "inventory_items": [
      {
        "inventory_id": "inventory:BK-01-MILK",
        "product_id": "product:MILK-WH",
        "product_name": "Whole Milk Gallon",
        "stock_level": 87,
        "price": 4.99
      }
    ]
  }
]
```

#### Get Store Details

```http
GET /freshmart/stores/{store_id}
```

**Example:**
```http
GET /freshmart/stores/store:BK-01
```

**Response:** Same as list item with full inventory details

#### List Inventory

```http
GET /freshmart/stores/inventory
```

**Query Parameters:**
- `store_id` (optional, string): Filter by store
- `low_stock_only` (optional, boolean): Only show low stock items

**Response:**
```json
[
  {
    "inventory_id": "inventory:BK-01-MILK",
    "store_id": "store:BK-01",
    "store_name": "FreshMart Brooklyn 1",
    "product_id": "product:MILK-WH",
    "product_name": "Whole Milk Gallon",
    "product_category": "Dairy",
    "stock_level": 87,
    "price": 4.99,
    "is_perishable": true
  }
]
```

### Customers

#### List Customers

```http
GET /freshmart/customers
```

**Response:**
```json
[
  {
    "customer_id": "customer:123",
    "customer_name": "Alex Thompson",
    "customer_email": "alex@example.com",
    "customer_phone": "555-0123",
    "customer_address": "123 Main St, Brooklyn"
  }
]
```

### Products

#### List Products

```http
GET /freshmart/products
```

**Response:**
```json
[
  {
    "product_id": "product:MILK-WH",
    "product_name": "Whole Milk Gallon",
    "product_category": "Dairy",
    "product_brand": "FreshMart",
    "base_price": 4.99,
    "is_perishable": true,
    "ingredients": ["Whole Milk", "Vitamin D"]
  }
]
```

### Couriers

#### List Couriers

```http
GET /freshmart/couriers
```

**Query Parameters:**
- `status` (optional, string): Filter by status (AVAILABLE, BUSY, OFF_DUTY)
- `store_id` (optional, string): Filter by home store

**Response:**
```json
[
  {
    "courier_id": "courier:C01",
    "courier_name": "John Delivery",
    "courier_phone": "555-0199",
    "courier_status": "BUSY",
    "home_store_id": "store:BK-01",
    "vehicle_type": "Van",
    "schedule_start": "08:00:00",
    "schedule_end": "16:00:00",
    "assigned_tasks": [
      {
        "task_id": "task:T001",
        "order_id": "order:FM-1001",
        "task_status": "IN_PROGRESS",
        "eta": "2025-01-15T15:30:00Z"
      }
    ]
  }
]
```

#### Get Courier Details

```http
GET /freshmart/couriers/{courier_id}
```

**Example:**
```http
GET /freshmart/couriers/courier:C01
```

**Response:** Same as list item with full task details

## Health & Monitoring

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy"
}
```

### Readiness Check

Verifies database connectivity:

```http
GET /ready
```

**Response (Ready):**
```json
{
  "status": "ready",
  "database": "connected"
}
```

**Response (Not Ready):**
```json
{
  "status": "not ready",
  "database": "disconnected"
}
```

### Query Statistics

```http
GET /stats
```

**Response:**
```json
{
  "postgresql": {
    "total_queries": 50,
    "total_time_ms": 125.5,
    "avg_time_ms": 2.51,
    "slow_queries": 0,
    "slowest_query_ms": 15.2,
    "slowest_query": "SELECT * FROM triples WHERE...",
    "by_operation": {
      "SELECT": { "count": 30, "total_ms": 75.2, "avg_ms": 2.5 },
      "INSERT": { "count": 20, "total_ms": 50.3, "avg_ms": 2.5 }
    }
  },
  "materialize": {
    "total_queries": 25,
    "total_time_ms": 45.2,
    "avg_time_ms": 1.81,
    "slow_queries": 0,
    "slowest_query_ms": 8.5,
    "slowest_query": "SELECT order_id FROM orders_flat_mv WHERE...",
    "by_operation": {
      "SET": { "count": 5, "total_ms": 3.2, "avg_ms": 0.64 },
      "SELECT": { "count": 20, "total_ms": 42.0, "avg_ms": 2.1 }
    }
  }
}
```

## Security Features

### DoS Protection

- **Order line creation limited to 100 products per request**
- Prevents excessive IN clause sizes in SQL queries
- Returns clear error messages when limits exceeded

Example error:
```json
{
  "detail": "Order contains 150 line items, which exceeds the maximum allowed (100)"
}
```

### Data Validation

- **NULL price handling** in dynamic pricing calculations
- COALESCE() used throughout to prevent NULL propagation
- Items with NULL prices filtered from inventory views
- Insufficient stock errors (no silent quantity modifications)

### Observability

All queries are logged with:
- Database type (PostgreSQL or Materialize)
- Operation type (SELECT, INSERT, UPDATE, DELETE, SET)
- Execution time in milliseconds
- Query text (truncated if > 200 chars)
- Parameters

Example log:
```
[Materialize] [SELECT] 15.67ms: SELECT order_id, order_number... | params={'limit': 100}
```

Slow queries (> 100ms) are logged as warnings.

## Error Responses

### Standard Error Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common HTTP Status Codes

- `200 OK` - Request successful
- `201 Created` - Resource created
- `204 No Content` - Delete successful
- `400 Bad Request` - Invalid input
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation failed
- `500 Internal Server Error` - Server error

## See Also

- [Architecture Guide](ARCHITECTURE.md) - CQRS pattern and data flow
- [Ontology Guide](ONTOLOGY_GUIDE.md) - Adding new entity types
- [Operations Guide](OPERATIONS.md) - Service management
