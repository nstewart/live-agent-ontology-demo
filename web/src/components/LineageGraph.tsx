import { useCallback, useMemo } from 'react';
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  Position,
  NodeMouseHandler,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

// Node type colors
const nodeColors = {
  source: { bg: '#3b82f6', border: '#1d4ed8', text: '#ffffff' }, // Blue
  view: { bg: '#6b7280', border: '#374151', text: '#ffffff' }, // Gray
  mv: { bg: '#10b981', border: '#059669', text: '#ffffff' }, // Green
  index: { bg: '#8b5cf6', border: '#6d28d9', text: '#ffffff' }, // Purple
};

// Custom node styles
const getNodeStyle = (type: keyof typeof nodeColors, isSelected: boolean = false) => ({
  background: nodeColors[type].bg,
  border: `2px solid ${isSelected ? '#fbbf24' : nodeColors[type].border}`,
  borderRadius: '8px',
  padding: '10px 16px',
  color: nodeColors[type].text,
  fontSize: '12px',
  fontWeight: 500,
  minWidth: '120px',
  textAlign: 'center' as const,
  cursor: 'pointer',
  boxShadow: isSelected ? '0 0 12px rgba(251, 191, 36, 0.6)' : undefined,
});

// Define the lineage nodes based on actual Materialize dependencies
// Queried from: mz_internal.mz_object_dependencies
const initialNodes: Node[] = [
  // Tier 0: Source
  {
    id: 'triples',
    position: { x: 0, y: 160 },
    data: { label: 'triples' },
    style: getNodeStyle('source'),
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
  },

  // Tier 1: Base views derived from triples
  {
    id: 'customers_flat',
    position: { x: 180, y: 0 },
    data: { label: 'customers_flat' },
    style: getNodeStyle('view'),
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
  },
  {
    id: 'stores_flat',
    position: { x: 180, y: 60 },
    data: { label: 'stores_flat' },
    style: getNodeStyle('view'),
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
  },
  {
    id: 'products_flat',
    position: { x: 180, y: 120 },
    data: { label: 'products_flat' },
    style: getNodeStyle('view'),
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
  },
  {
    id: 'order_lines_base',
    position: { x: 180, y: 180 },
    data: { label: 'order_lines_base' },
    style: getNodeStyle('view'),
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
  },
  {
    id: 'delivery_tasks_flat',
    position: { x: 180, y: 240 },
    data: { label: 'delivery_tasks_flat' },
    style: getNodeStyle('view'),
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
  },

  // Tier 2: First-level MVs
  {
    id: 'orders_flat_mv',
    position: { x: 380, y: 30 },
    data: { label: 'orders_flat_mv' },
    style: getNodeStyle('mv'),
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
  },
  {
    id: 'order_lines_flat_mv',
    position: { x: 380, y: 150 },
    data: { label: 'order_lines_flat_mv' },
    style: getNodeStyle('mv'),
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
  },

  // Tier 3: Second-level MVs
  {
    id: 'store_inventory_mv',
    position: { x: 580, y: 210 },
    data: { label: 'store_inventory_mv' },
    style: getNodeStyle('mv'),
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
  },

  // Tier 4: Final Data Products (two separate branches)
  {
    id: 'orders_with_lines_mv',
    position: { x: 580, y: 60 },
    data: { label: 'orders_with_lines_mv' },
    style: {
      ...getNodeStyle('mv'),
      border: '3px solid #059669',
      boxShadow: '0 0 10px rgba(16, 185, 129, 0.4)',
    },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
  },
  {
    id: 'inventory_items_with_dynamic_pricing',
    position: { x: 780, y: 180 },
    data: { label: 'dynamic_pricing' },
    style: getNodeStyle('view'),
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
  },
  {
    id: 'inventory_items_with_dynamic_pricing_mv',
    position: { x: 980, y: 180 },
    data: { label: 'dynamic_pricing_mv' },
    style: {
      ...getNodeStyle('mv'),
      border: '3px solid #059669',
      boxShadow: '0 0 10px rgba(16, 185, 129, 0.4)',
    },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
  },
];

// Define edges with animated flow
const edgeStyle = {
  stroke: '#94a3b8',
  strokeWidth: 2,
};

// Edges based on actual Materialize dependencies from mz_internal.mz_object_dependencies
const initialEdges: Edge[] = [
  // Tier 0 → Tier 1: triples to base views
  { id: 'e-triples-customers', source: 'triples', target: 'customers_flat', style: edgeStyle, animated: true },
  { id: 'e-triples-stores', source: 'triples', target: 'stores_flat', style: edgeStyle, animated: true },
  { id: 'e-triples-products', source: 'triples', target: 'products_flat', style: edgeStyle, animated: true },
  { id: 'e-triples-orderlines', source: 'triples', target: 'order_lines_base', style: edgeStyle, animated: true },
  { id: 'e-triples-tasks', source: 'triples', target: 'delivery_tasks_flat', style: edgeStyle, animated: true },

  // Tier 0 → Tier 2: triples directly to orders_flat_mv
  { id: 'e-triples-orders', source: 'triples', target: 'orders_flat_mv', style: edgeStyle, animated: true },

  // Tier 1 → Tier 2: base views to order_lines_flat_mv
  { id: 'e-orderlines-mv', source: 'order_lines_base', target: 'order_lines_flat_mv', style: edgeStyle, animated: true },
  { id: 'e-products-orderlines', source: 'products_flat', target: 'order_lines_flat_mv', style: edgeStyle, animated: true },

  // Tier 1,2 → Tier 3: to store_inventory_mv (depends on triples, products_flat, stores_flat, orders_flat_mv, order_lines_flat_mv)
  { id: 'e-triples-inventory', source: 'triples', target: 'store_inventory_mv', style: edgeStyle, animated: true },
  { id: 'e-products-inventory', source: 'products_flat', target: 'store_inventory_mv', style: edgeStyle, animated: true },
  { id: 'e-stores-inventory', source: 'stores_flat', target: 'store_inventory_mv', style: edgeStyle, animated: true },
  { id: 'e-ordersflat-inventory', source: 'orders_flat_mv', target: 'store_inventory_mv', style: edgeStyle, animated: true },
  { id: 'e-orderlinesflat-inventory', source: 'order_lines_flat_mv', target: 'store_inventory_mv', style: edgeStyle, animated: true },

  // Tier 1,2 → Tier 4: to orders_with_lines_mv
  { id: 'e-customers-final', source: 'customers_flat', target: 'orders_with_lines_mv', style: edgeStyle, animated: true },
  { id: 'e-stores-final', source: 'stores_flat', target: 'orders_with_lines_mv', style: edgeStyle, animated: true },
  { id: 'e-tasks-final', source: 'delivery_tasks_flat', target: 'orders_with_lines_mv', style: edgeStyle, animated: true },
  { id: 'e-ordersflat-final', source: 'orders_flat_mv', target: 'orders_with_lines_mv', style: edgeStyle, animated: true },
  { id: 'e-orderlinesflat-final', source: 'order_lines_flat_mv', target: 'orders_with_lines_mv', style: edgeStyle, animated: true },

  // Tier 2,3 → Tier 4: to dynamic_pricing (depends on store_inventory_mv, orders_flat_mv, order_lines_flat_mv)
  { id: 'e-inventory-pricing', source: 'store_inventory_mv', target: 'inventory_items_with_dynamic_pricing', style: edgeStyle, animated: true },
  { id: 'e-ordersflat-pricing', source: 'orders_flat_mv', target: 'inventory_items_with_dynamic_pricing', style: edgeStyle, animated: true },
  { id: 'e-orderlinesflat-pricing', source: 'order_lines_flat_mv', target: 'inventory_items_with_dynamic_pricing', style: edgeStyle, animated: true },

  // Tier 4 → Tier 5: dynamic_pricing to dynamic_pricing_mv
  { id: 'e-pricing-mv', source: 'inventory_items_with_dynamic_pricing', target: 'inventory_items_with_dynamic_pricing_mv', style: edgeStyle, animated: true },
];

// Node type mapping for styling
const nodeTypeMap: Record<string, keyof typeof nodeColors> = {
  triples: 'source',
  customers_flat: 'view',
  stores_flat: 'view',
  products_flat: 'view',
  order_lines_base: 'view',
  delivery_tasks_flat: 'view',
  orders_flat_mv: 'mv',
  order_lines_flat_mv: 'mv',
  orders_with_lines_mv: 'mv',
  store_inventory_mv: 'mv',
  inventory_items_with_dynamic_pricing: 'view',
  inventory_items_with_dynamic_pricing_mv: 'mv',
};

interface LineageGraphProps {
  selectedNodeId?: string | null;
  onNodeClick?: (nodeId: string) => void;
}

export function LineageGraph({ selectedNodeId, onNodeClick }: LineageGraphProps) {
  // Create nodes with selection state - using useMemo so it updates when selectedNodeId changes
  const nodes = useMemo(() => {
    return initialNodes.map((node) => {
      const nodeType = nodeTypeMap[node.id] || 'view';
      const isSelected = node.id === selectedNodeId;
      const isHighlighted = node.id === 'orders_with_lines_mv';

      return {
        ...node,
        style: isHighlighted && !isSelected
          ? {
              ...getNodeStyle(nodeType, isSelected),
              border: '3px solid #059669',
              boxShadow: '0 0 10px rgba(16, 185, 129, 0.4)',
            }
          : getNodeStyle(nodeType, isSelected),
      };
    });
  }, [selectedNodeId]);

  const edges = initialEdges;

  const handleNodeClick: NodeMouseHandler = useCallback(
    (_, node) => {
      if (onNodeClick) {
        onNodeClick(node.id);
      }
    },
    [onNodeClick]
  );

  return (
    <div className="w-full">
      {/* Legend */}
      <div className="flex gap-6 mb-4 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ background: nodeColors.source.bg }} />
          <span className="text-gray-600">Source (CDC)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ background: nodeColors.view.bg }} />
          <span className="text-gray-600">View</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ background: nodeColors.mv.bg }} />
          <span className="text-gray-600">Materialized View</span>
        </div>
        {selectedNodeId && (
          <div className="flex items-center gap-2 ml-auto">
            <div className="w-4 h-4 rounded border-2 border-yellow-400" style={{ background: 'transparent' }} />
            <span className="text-gray-600">Selected</span>
          </div>
        )}
      </div>

      {/* Graph */}
      <div className="h-[350px] w-full border border-gray-200 rounded-lg bg-gray-50">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodeClick={handleNodeClick}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={true}
          panOnDrag={false}
          zoomOnScroll={false}
          zoomOnPinch={false}
          zoomOnDoubleClick={false}
          preventScrolling={false}
        >
          <Background color="#e5e7eb" gap={16} />
        </ReactFlow>
      </div>

      {/* Description */}
      <p className="mt-3 text-sm text-gray-500">
        Two data products from the same <span className="font-medium text-blue-600">triples</span> source:{' '}
        <span className="font-medium text-green-600">orders_with_lines_mv</span> (order details) and{' '}
        <span className="font-medium text-green-600">dynamic_pricing_mv</span> (live pricing with 9 factors).
        The API joins them to show live prices on order line items. Click any node to view its SQL.
      </p>
    </div>
  );
}

export default LineageGraph;
