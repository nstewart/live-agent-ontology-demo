# Implementation Review: Order Line Items Feature

**Status**: Ready for Review & Approval
**Date**: November 24, 2025
**Stakeholders**: Product, Architecture, Development

---

## Overview

This document summarizes the complete planning for the Order Line Items feature, combining insights from Product Management and Architecture teams. **Please review and approve before development begins.**

## 📋 Planning Documents

Three comprehensive documents have been created:

1. **[Product Brief](./PRODUCT_BRIEF_ORDER_LINE_ITEMS.md)** (302 lines) - Problem definition, user stories, success metrics
2. **[Architecture Guidance](./ARCHITECTURE_GUIDANCE_ORDER_LINE_ITEMS.md)** (1,319 lines) - Technical design, patterns, implementation details
3. **This Review** - Executive summary and approval checklist

---

## 🎯 Feature Summary

### What We're Building
Enable operations staff to create orders with detailed line items (products), showing:
- Real-time inventory availability per store
- Shopping cart interface with quantity selection
- Product metadata (perishable status)
- Expandable order views to see line items
- Search orders by product name

### Why It Matters
- **Order Accuracy**: From 88% to 97% (orders created with items in stock)
- **Order Creation Time**: From 3 minutes to 90 seconds
- **Cancellation Rate**: Reduce stock-related cancellations by 75%
- **Customer Service**: 40% faster resolution time

---

## 🏗️ Architecture Decisions

### 1. Data Model: OrderLine Entity
```
Subject ID Format: orderline:FM-1001-001, orderline:FM-1001-002
Properties: line_of_order, line_product, quantity, unit_price, line_amount, line_sequence
Storage: Triple-store pattern (consistent with existing entities)
```

**Key Decision**: Snapshot product price at order time for audit trail

### 2. Materialization Strategy
```sql
-- Three-tier view hierarchy:
1. order_lines_base (non-materialized for flexibility)
2. order_lines_flat_mv (dedicated line item queries)
3. orders_with_lines_mv (nested JSONB aggregation for UI)

-- Performance: Sub-2 second materialization, <500ms UI expansion
```

### 3. Transaction Boundaries
- Single ACID transaction: Order + Line Items + Inventory Check
- Optimistic locking with retry logic (max 3 retries)
- Database triggers for referential integrity
- Compensation patterns for update failures

### 4. Search Integration
```javascript
// OpenSearch nested field mapping
{
  "line_items": {
    "type": "nested",
    "properties": {
      "product_id": { "type": "keyword" },
      "product_name": { "type": "text" },
      "quantity": { "type": "integer" },
      "line_amount": { "type": "float" },
      "perishable": { "type": "boolean" }
    }
  }
}
```

### 5. Real-time Updates
- Zero WebSocket event consolidation for DELETE+INSERT pairs
- Batch line item updates by order to reduce traffic
- Extended schema with order_lines table and relationships

### 6. UI State Management
- Zustand-based shopping cart store with local persistence
- Real-time inventory validation during product selection
- Expandable row pattern for orders table
- Optimistic updates synchronized with Zero WebSocket

---

## ✅ Acceptance Criteria

### Data Model
- [ ] OrderLine class added to ontology with 7 properties
- [ ] Triple CRUD operations support bulk insert of line items
- [ ] Materialized views refresh in <2 seconds for 1000 new line items
- [ ] Composite indexes created on (order_id, line_sequence)

### UI/UX
- [ ] Store selection dynamically filters products based on inventory
- [ ] Shopping cart shows: product name, quantity, unit price, line total, perishable indicator
- [ ] Running order total calculates automatically
- [ ] Validation prevents adding out-of-stock items
- [ ] Expandable rows show line items in nested table format
- [ ] Order creation flow completes in <3 seconds with 50 line items

### Search
- [ ] OpenSearch mapping includes nested line_items field
- [ ] Product name search returns matching orders
- [ ] Search performance maintains <500ms p95 latency
- [ ] Denormalized order data includes all line items

### Performance
- [ ] Order expansion renders in <500ms for 20 line items
- [ ] Product search across 100k orders returns in <1 second
- [ ] WebSocket updates throttled to 10/sec per client
- [ ] Maximum 100 line items per order enforced

---

## 🚨 Open Questions Requiring Decisions

### Critical (Block Development)
1. **Inventory Reservation**: Optimistic locking OR eventual consistency?
   - **DECISION**: No locking - eventual consistency
   - **Rationale**: Simplified implementation, acceptable for grocery fulfillment model

2. **Price Snapshotting**: Snapshot OR reference current price?
   - **DECISION**: Snapshot at order time ✅
   - **Rationale**: Audit trail integrity, pricing accuracy for historical orders

3. **Historical Data**: Backfill existing orders OR start fresh?
   - **Recommendation**: Start fresh from implementation date
   - **Rationale**: Clean data boundary, avoids migration complexity

### Important (Can Defer)
4. **Partial Fulfillment**: Allow OR require full cancellation?
   - **Recommendation**: Defer to v2, full cancellation for MVP

5. **Stock Visibility**: Exact numbers OR indicators?
   - **Recommendation**: Show indicators (In Stock/Low/Out) with exact numbers on hover

6. **Mobile Support**: Required for warehouse staff?
   - **Recommendation**: Yes, use responsive expandable pattern

---

## 📦 Implementation Scope

### In Scope (MVP - 6 weeks)
✅ OrderLine entity with full CRUD
✅ Store-filtered product selection
✅ Shopping cart UI with validation
✅ Expandable order views
✅ Materialized views with JSONB aggregation
✅ OpenSearch nested field integration
✅ Zero WebSocket real-time updates
✅ Batch triple insertion
✅ Transaction consistency with retries

### Out of Scope (Future)
❌ Bulk order import from CSV
❌ Product substitution suggestions
❌ Order templates
❌ Analytics dashboard
❌ Inventory reservation system
❌ Backorder management
❌ Product bundles/kits
❌ Order splitting across stores

---

## ⚠️ Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Materialization lag increases | Medium | High | Pre-aggregate queries, monitor cluster capacity |
| WebSocket drops during creation | Low | High | Optimistic UI + retry logic |
| Search performance degradation | Medium | Medium | Nested fields efficiently, dedicated index |
| Training gap for complex UI | High | Medium | Phased rollout + training materials |
| Data quality during migration | Medium | High | Validation scripts + reconciliation |
| Inventory sync delays | Low | High | Real-time checks + circuit breakers |

---

## 📅 Implementation Timeline

### Phase 1: Foundation (Week 1-2)
- Create OrderLine ontology class
- Implement triple-store CRUD with bulk operations
- Create materialized views and indexes
- Update Zero schema and WebSocket handlers

### Phase 2: UI Development (Week 3-4)
- Build product selector with store filtering
- Implement shopping cart component with Zustand
- Add expandable rows to orders table
- Integrate real-time updates

### Phase 3: Search & Analytics (Week 5)
- Update OpenSearch mappings
- Implement product search functionality
- Add line items to sync worker
- Create operational reports

### Phase 4: Testing & Rollout (Week 6)
- End-to-end testing with production-like data
- Performance testing and optimization
- User acceptance testing with operations team
- Gradual rollout with feature flags

---

## 🔍 Code Examples & Patterns

The Architecture Guidance document includes complete examples for:
- SQL schemas and materialized view definitions (100+ lines)
- Python service layer with transaction patterns (200+ lines)
- TypeScript UI components and state management (150+ lines)
- OpenSearch mapping and queries (50+ lines)
- Zero WebSocket integration (75+ lines)
- Migration scripts (100+ lines)
- Test fixtures and scenarios (50+ lines)

---

## 💰 Resource Requirements

### Technical
- Materialize cluster capacity: +2 materialized views (verify available resources)
- OpenSearch: +1 nested field per order (monitor heap usage)
- PostgreSQL: +7 predicates per line item (estimate 5-10 items/order)
- Zero: +1 collection (order_lines)

### Organizational
- Product Manager: Review and approve scope
- Architect: Review technical design (this document)
- Backend Developer: 2-3 weeks full-time
- Frontend Developer: 2-3 weeks full-time
- QA Engineer: 1 week for comprehensive testing
- Operations: 2-3 days for UAT and training

---

## ✋ Review & Approval Checklist

### Product Review
- [ ] Problem statement aligns with user needs
- [ ] Success metrics are measurable and achievable
- [ ] User stories cover all key personas
- [ ] Scope is appropriate for 6-week timeline
- [ ] Open questions have clear recommendations
- [ ] Non-goals are explicitly stated

### Architecture Review
- [ ] Triple-store entity design is consistent with ontology
- [ ] Materialization strategy is performant and scalable
- [ ] Transaction boundaries ensure data consistency
- [ ] OpenSearch integration maintains search performance
- [ ] Zero WebSocket patterns are efficient
- [ ] UI state management is appropriate for complexity
- [ ] Security and validation are addressed
- [ ] Monitoring and alerting are defined

### Development Review
- [ ] Implementation plan is clear and actionable
- [ ] Technical dependencies are identified
- [ ] Code examples provide sufficient guidance
- [ ] Testing strategy is comprehensive
- [ ] Rollback plan exists for issues
- [ ] Documentation requirements are clear

---

## 📝 Next Steps

1. **Stakeholder Review** (1-2 days)
   - Product Manager approves scope and metrics
   - Architect approves technical design
   - Development team confirms feasibility

2. **Decision Resolution** (1 day)
   - Resolve 3 critical open questions
   - Document decisions in this review

3. **Development Kickoff** (Day 1)
   - Create GitHub issues/tickets from implementation plan
   - Set up feature branch and CI/CD pipeline
   - Schedule daily standups for 6-week sprint

4. **Weekly Check-ins**
   - Monday: Progress review and blocker identification
   - Friday: Demo completed work to stakeholders

---

## 📚 Reference Documents

- [Product Brief](./PRODUCT_BRIEF_ORDER_LINE_ITEMS.md) - Full problem analysis and requirements
- [Architecture Guidance](./ARCHITECTURE_GUIDANCE_ORDER_LINE_ITEMS.md) - Detailed technical design
- [Current Ontology](./ONTOLOGY.md) - Existing entity definitions
- [Data Model](./DATA_MODEL.md) - Triple-store implementation
- [Architecture Overview](./ARCHITECTURE.md) - System architecture

---

## 🎯 Definition of Done

This feature is considered complete when:
1. All acceptance criteria are met and tested
2. Performance benchmarks are achieved
3. User acceptance testing passes with operations team
4. Documentation is updated (user guides, API docs)
5. Monitoring and alerting are configured
6. Code review is completed and approved
7. Feature is deployed to production with feature flag
8. Post-launch metrics tracking is enabled

---

**Ready to proceed?** Please review the complete planning documents and provide approval to begin development.
