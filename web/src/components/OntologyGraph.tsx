import { useMemo, useEffect } from 'react'
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  useNodesState,
  useEdgesState,
  Position,
  MarkerType,
  ReactFlowProvider,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useQuery } from '@tanstack/react-query'
import { ontologyApi } from '../api/client'

// Node colors by category
const nodeColors = {
  entity: { bg: '#10b981', border: '#059669', text: '#ffffff' }, // Green - main entities
  reference: { bg: '#6366f1', border: '#4f46e5', text: '#ffffff' }, // Indigo - referenced entities
  standalone: { bg: '#64748b', border: '#475569', text: '#ffffff' }, // Slate - no relationships
}

// Get node style based on type
const getNodeStyle = (type: keyof typeof nodeColors) => ({
  background: nodeColors[type].bg,
  border: `2px solid ${nodeColors[type].border}`,
  borderRadius: '8px',
  padding: '12px 16px',
  color: nodeColors[type].text,
  fontSize: '13px',
  fontWeight: 600,
  minWidth: '130px',
  textAlign: 'center' as const,
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
})

// Edge style
const edgeStyle = {
  stroke: '#94a3b8',
  strokeWidth: 2,
}

// Inner component that uses ReactFlow hooks (must be inside ReactFlowProvider)
function OntologyGraphInner() {
  // Fetch classes and properties
  const { data: classes = [] } = useQuery({
    queryKey: ['ontology-classes'],
    queryFn: () => ontologyApi.listClasses().then(r => r.data),
  })

  const { data: properties = [] } = useQuery({
    queryKey: ['ontology-properties'],
    queryFn: () => ontologyApi.listProperties().then(r => r.data),
  })

  // Build nodes and edges from data
  const { nodes: computedNodes, edges: computedEdges } = useMemo(() => {
    if (!classes.length) {
      return { nodes: [], edges: [] }
    }

    // Find entity_ref properties (relationships between classes)
    const relationships = properties.filter(p => p.range_kind === 'entity_ref' && p.range_class_id)

    // Track which classes have incoming/outgoing relationships
    const hasOutgoing = new Set<number>()
    const hasIncoming = new Set<number>()
    relationships.forEach(rel => {
      hasOutgoing.add(rel.domain_class_id)
      if (rel.range_class_id) hasIncoming.add(rel.range_class_id)
    })

    // Count scalar properties per class
    const scalarPropsCount: Record<number, number> = {}
    properties.forEach(p => {
      if (p.range_kind !== 'entity_ref') {
        scalarPropsCount[p.domain_class_id] = (scalarPropsCount[p.domain_class_id] || 0) + 1
      }
    })

    // Layout: arrange classes in a grid with relationships considered
    const sortedClasses = [...classes].sort((a, b) => {
      const aRels = (hasOutgoing.has(a.id) ? 1 : 0) + (hasIncoming.has(a.id) ? 1 : 0)
      const bRels = (hasOutgoing.has(b.id) ? 1 : 0) + (hasIncoming.has(b.id) ? 1 : 0)
      return bRels - aRels
    })

    // Calculate positions - arrange in rows
    const nodesPerRow = Math.ceil(Math.sqrt(classes.length))
    const nodeWidth = 160
    const nodeHeight = 80
    const horizontalGap = 80
    const verticalGap = 100

    const nodes: Node[] = sortedClasses.map((cls, index) => {
      const row = Math.floor(index / nodesPerRow)
      const col = index % nodesPerRow

      // Determine node type based on relationships
      let nodeType: keyof typeof nodeColors = 'standalone'
      if (hasOutgoing.has(cls.id)) {
        nodeType = 'entity'
      } else if (hasIncoming.has(cls.id)) {
        nodeType = 'reference'
      }

      const scalarCount = scalarPropsCount[cls.id] || 0

      return {
        id: `class-${cls.id}`,
        position: {
          x: col * (nodeWidth + horizontalGap),
          y: row * (nodeHeight + verticalGap),
        },
        data: {
          label: (
            <div className="text-center">
              <div className="font-semibold">{cls.class_name}</div>
              <div className="text-xs opacity-75 mt-0.5">{cls.prefix}:</div>
              {scalarCount > 0 && (
                <div className="text-xs opacity-60">{scalarCount} props</div>
              )}
            </div>
          ),
          className: cls.class_name,
        },
        style: getNodeStyle(nodeType),
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
      }
    })

    // Create edges for entity_ref relationships
    const edges: Edge[] = relationships.map((rel) => ({
      id: `edge-${rel.id}`,
      source: `class-${rel.domain_class_id}`,
      target: `class-${rel.range_class_id}`,
      label: rel.prop_name,
      labelStyle: {
        fontSize: '10px',
        fontWeight: 500,
        fill: '#64748b',
      },
      labelBgStyle: {
        fill: '#f8fafc',
        fillOpacity: 0.9,
      },
      labelBgPadding: [4, 6] as [number, number],
      labelBgBorderRadius: 4,
      style: edgeStyle,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: '#94a3b8',
        width: 20,
        height: 20,
      },
    }))

    return { nodes, edges }
  }, [classes, properties])

  const [nodes, setNodes] = useNodesState<Node>([])
  const [edges, setEdges] = useEdgesState<Edge>([])

  // Update nodes and edges when computed values change
  useEffect(() => {
    if (computedNodes.length > 0) {
      setNodes(computedNodes)
      setEdges(computedEdges)
    }
  }, [computedNodes, computedEdges, setNodes, setEdges])

  if (!classes.length) {
    return (
      <div className="h-[300px] flex items-center justify-center bg-gray-50 rounded-lg border border-gray-200">
        <p className="text-gray-500">No classes defined yet</p>
      </div>
    )
  }

  // Calculate dynamic height based on number of rows
  const nodesPerRow = Math.ceil(Math.sqrt(classes.length))
  const numRows = Math.ceil(classes.length / nodesPerRow)
  const graphHeight = Math.max(350, numRows * 180)

  return (
    <div className="w-full">
      {/* Legend */}
      <div className="flex flex-wrap gap-4 mb-3 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ background: nodeColors.entity.bg }} />
          <span className="text-gray-600">Entity (has relationships)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ background: nodeColors.reference.bg }} />
          <span className="text-gray-600">Referenced entity</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ background: nodeColors.standalone.bg }} />
          <span className="text-gray-600">Standalone</span>
        </div>
      </div>

      {/* Graph */}
      <div
        className="w-full border border-gray-200 rounded-lg bg-gray-50"
        style={{ height: `${graphHeight}px` }}
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          nodesDraggable={true}
          nodesConnectable={false}
          elementsSelectable={true}
          panOnDrag={true}
          zoomOnScroll={true}
          zoomOnPinch={true}
          zoomOnDoubleClick={false}
          preventScrolling={false}
          minZoom={0.3}
          maxZoom={1.5}
        >
          <Background color="#e5e7eb" gap={20} />
        </ReactFlow>
      </div>

      {/* Description */}
      <p className="mt-3 text-sm text-gray-500">
        Ontology schema visualization. Arrows represent <code className="bg-gray-100 px-1 rounded text-xs">entity_ref</code> properties linking classes.
      </p>
    </div>
  )
}

// Wrapper component that provides ReactFlowProvider context
export function OntologyGraph() {
  return (
    <ReactFlowProvider>
      <OntologyGraphInner />
    </ReactFlowProvider>
  )
}

export default OntologyGraph
