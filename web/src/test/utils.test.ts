import { describe, it, expect } from 'vitest'
import {
  formatDate,
  formatAmount,
  getStatusColor,
  extractPrefix,
  filterPropertiesByClass,
  groupOrdersByStatus,
  calculateOrderTotalsByStatus,
} from './utils'
import { mockOntologyProperties, mockOrders } from './mocks'

describe('formatDate', () => {
  it('returns "-" for null', () => {
    expect(formatDate(null)).toBe('-')
  })

  it('formats valid date string', () => {
    const result = formatDate('2024-01-15T14:00:00Z')
    expect(result).toBeTruthy()
    expect(result).not.toBe('-')
  })
})

describe('getStatusColor', () => {
  it('returns correct color for CREATED', () => {
    expect(getStatusColor('CREATED')).toContain('gray')
  })

  it('returns correct color for OUT_FOR_DELIVERY', () => {
    expect(getStatusColor('OUT_FOR_DELIVERY')).toContain('blue')
  })

  it('returns correct color for DELIVERED', () => {
    expect(getStatusColor('DELIVERED')).toContain('green')
  })

  it('returns correct color for CANCELLED', () => {
    expect(getStatusColor('CANCELLED')).toContain('red')
  })

  it('returns default color for unknown status', () => {
    expect(getStatusColor('UNKNOWN')).toContain('gray')
  })

  it('handles null status', () => {
    expect(getStatusColor(null)).toContain('gray')
  })
})

describe('extractPrefix', () => {
  it('extracts prefix from subject ID', () => {
    expect(extractPrefix('customer:123')).toBe('customer')
    expect(extractPrefix('order:FM-1001')).toBe('order')
    expect(extractPrefix('store:BK-01')).toBe('store')
  })

  it('handles IDs with multiple colons', () => {
    expect(extractPrefix('task:T:123')).toBe('task')
  })
})

describe('filterPropertiesByClass', () => {
  it('returns properties for specified class', () => {
    const customerProps = filterPropertiesByClass(mockOntologyProperties, 1)
    expect(customerProps.length).toBe(1)
    expect(customerProps[0].prop_name).toBe('customer_name')
  })

  it('returns empty array for non-existent class', () => {
    const props = filterPropertiesByClass(mockOntologyProperties, 999)
    expect(props).toEqual([])
  })

  it('returns all properties for matching class', () => {
    const orderProps = filterPropertiesByClass(mockOntologyProperties, 2)
    expect(orderProps.every((p) => p.domain_class_id === 2)).toBe(true)
  })
})

describe('groupOrdersByStatus', () => {
  it('groups orders by status', () => {
    const grouped = groupOrdersByStatus(mockOrders)
    expect(grouped['OUT_FOR_DELIVERY']).toHaveLength(1)
    expect(grouped['DELIVERED']).toHaveLength(1)
  })

  it('returns empty object for empty array', () => {
    const grouped = groupOrdersByStatus([])
    expect(Object.keys(grouped)).toHaveLength(0)
  })

  it('handles orders with same status', () => {
    const orders = [
      { ...mockOrders[0], order_status: 'CREATED' },
      { ...mockOrders[1], order_status: 'CREATED' },
    ]
    const grouped = groupOrdersByStatus(orders)
    expect(grouped['CREATED']).toHaveLength(2)
  })
})

describe('formatAmount', () => {
  it('formats number amounts', () => {
    expect(formatAmount(45.99)).toBe('45.99')
    expect(formatAmount(100)).toBe('100.00')
  })

  it('formats string amounts (API may return decimals as strings)', () => {
    // This test would have caught the toFixed bug!
    expect(formatAmount('45.99')).toBe('45.99')
    expect(formatAmount('100')).toBe('100.00')
    expect(formatAmount('32.5')).toBe('32.50')
  })

  it('handles null and undefined', () => {
    expect(formatAmount(null)).toBe('0.00')
    expect(formatAmount(undefined)).toBe('0.00')
  })

  it('handles invalid strings', () => {
    expect(formatAmount('invalid')).toBe('0.00')
    expect(formatAmount('')).toBe('0.00')
  })
})

describe('calculateOrderTotalsByStatus', () => {
  it('calculates totals for each status', () => {
    const totals = calculateOrderTotalsByStatus(mockOrders)
    expect(totals['OUT_FOR_DELIVERY']).toBe(45.99)
    expect(totals['DELIVERED']).toBe(32.5)
  })

  it('handles orders with null totals', () => {
    const orders = [
      { ...mockOrders[0], order_total_amount: null },
    ]
    const totals = calculateOrderTotalsByStatus(orders)
    expect(totals['OUT_FOR_DELIVERY']).toBe(0)
  })

  it('handles orders with string amounts (API returns decimals as strings)', () => {
    // This test would have caught the toFixed bug!
    const orders = [
      { ...mockOrders[0], order_total_amount: '45.99' as unknown as number },
      { ...mockOrders[1], order_total_amount: '32.50' as unknown as number },
    ]
    const totals = calculateOrderTotalsByStatus(orders)
    expect(totals['OUT_FOR_DELIVERY']).toBe(45.99)
    expect(totals['DELIVERED']).toBe(32.5)
  })

  it('returns empty object for empty array', () => {
    const totals = calculateOrderTotalsByStatus([])
    expect(Object.keys(totals)).toHaveLength(0)
  })
})
