import { useState, useMemo } from 'react'
import { useZero, useQuery } from '@rocicorp/zero/react'
import {
  Truck,
  Package,
  ChevronDown,
  ChevronRight,
  Info,
  Store,
  ShoppingCart,
} from 'lucide-react'
import { Schema } from '../schema'

// Bundle type from Zero
interface Bundle {
  bundle_id: string
  store_id: string | null
  store_name: string | null
  orders: string[] | null
  bundle_size: number | null
}

export default function BundlingPage() {
  const [howItWorksOpen, setHowItWorksOpen] = useState(true)

  // Zero queries
  const z = useZero<Schema>()

  // Query all bundles
  const bundlesQuery = useMemo(() => z.query.delivery_bundles_mv, [z])
  const [bundlesData] = useQuery(bundlesQuery)
  const bundles = (bundlesData || []) as Bundle[]

  // Group bundles by store
  const bundlesByStore = useMemo(() => {
    const grouped: Record<string, Bundle[]> = {}
    for (const bundle of bundles) {
      const storeKey = bundle.store_id || 'unknown'
      if (!grouped[storeKey]) {
        grouped[storeKey] = []
      }
      grouped[storeKey].push(bundle)
    }
    // Sort bundles within each store by size (descending)
    for (const storeKey of Object.keys(grouped)) {
      grouped[storeKey].sort((a, b) => (b.bundle_size || 0) - (a.bundle_size || 0))
    }
    return grouped
  }, [bundles])

  // Filter to multi-order bundles (size > 1)
  const multiBundles = bundles.filter((b) => (b.bundle_size || 0) > 1)
  const singletonBundles = bundles.filter((b) => (b.bundle_size || 0) === 1)

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3">
          <Truck className="h-8 w-8 text-green-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Delivery Bundling</h1>
            <p className="text-gray-600">
              Mutually recursive constraint satisfaction
            </p>
          </div>
        </div>
      </div>

      {/* How It Works Section */}
      <div className="bg-white rounded-lg shadow mb-6">
        <button
          onClick={() => setHowItWorksOpen(!howItWorksOpen)}
          className="w-full p-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
        >
          <div className="flex items-center gap-2">
            {howItWorksOpen ? (
              <ChevronDown className="h-5 w-5 text-gray-500" />
            ) : (
              <ChevronRight className="h-5 w-5 text-gray-500" />
            )}
            <Info className="h-5 w-5 text-blue-500" />
            <div className="text-left">
              <h3 className="text-lg font-semibold text-gray-900">How It Works</h3>
              <p className="text-xs text-gray-500">
                Understanding Materialize's WITH MUTUALLY RECURSIVE
              </p>
            </div>
          </div>
        </button>
        {howItWorksOpen && (
          <div className="p-6 pt-0 border-t">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Left: Mutual Recursion Explanation */}
              <div>
                <h4 className="font-medium text-gray-900 mb-4">What is Mutual Recursion?</h4>
                <p className="text-sm text-gray-600 mb-4">
                  Traditional queries run once and return results. Mutually recursive queries have
                  multiple definitions that <span className="font-semibold text-gray-900">reference each other</span> and
                  run repeatedly until no new results are found (a "fixed point").
                </p>

                {/* Visual Diagram */}
                <div className="bg-gradient-to-br from-blue-50 to-green-50 rounded-xl p-6 mb-4">
                  <div className="flex items-center justify-center gap-4">
                    {/* Compatible Pairs Box */}
                    <div className="bg-white rounded-lg shadow-md p-4 w-40 text-center border-2 border-blue-300">
                      <div className="text-blue-600 font-semibold text-sm mb-1">Compatible Pairs</div>
                      <div className="text-xs text-gray-500">Which orders CAN be bundled?</div>
                    </div>

                    {/* Arrows */}
                    <div className="flex flex-col items-center gap-1">
                      <div className="flex items-center">
                        <span className="text-green-500 text-lg">→</span>
                      </div>
                      <div className="text-xs text-gray-400 font-medium">feeds into</div>
                      <div className="flex items-center">
                        <span className="text-blue-500 text-lg">←</span>
                      </div>
                    </div>

                    {/* Bundle Membership Box */}
                    <div className="bg-white rounded-lg shadow-md p-4 w-40 text-center border-2 border-green-300">
                      <div className="text-green-600 font-semibold text-sm mb-1">Bundle Membership</div>
                      <div className="text-xs text-gray-500">Which bundle does each order join?</div>
                    </div>
                  </div>

                  {/* Iteration indicator */}
                  <div className="mt-4 flex items-center justify-center gap-2">
                    <div className="flex items-center gap-1">
                      <span className="inline-block w-2 h-2 rounded-full bg-gray-300"></span>
                      <span className="inline-block w-2 h-2 rounded-full bg-gray-400"></span>
                      <span className="inline-block w-2 h-2 rounded-full bg-gray-500"></span>
                      <span className="inline-block w-2 h-2 rounded-full bg-green-500"></span>
                    </div>
                    <span className="text-xs text-gray-500">Iterates until stable</span>
                  </div>
                </div>

                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                  <div className="flex items-start gap-2">
                    <span className="text-amber-500 mt-0.5">💡</span>
                    <p className="text-xs text-amber-800">
                      <span className="font-semibold">Why Materialize?</span> Most databases can't handle mutual recursion.
                      Materialize maintains these complex recursive results incrementally—when an order changes,
                      only affected bundles recompute, not everything.
                    </p>
                  </div>
                </div>
              </div>

              {/* Right: How Bundling Works */}
              <div>
                <h4 className="font-medium text-gray-900 mb-4">How Orders Get Bundled</h4>

                {/* Step by step */}
                <div className="space-y-3 mb-4">
                  <div className="flex gap-3">
                    <div className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-bold">1</div>
                    <div>
                      <div className="text-sm font-medium text-gray-900">Each order starts alone</div>
                      <div className="text-xs text-gray-500">Every CREATED order begins in its own bundle</div>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <div className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-bold">2</div>
                    <div>
                      <div className="text-sm font-medium text-gray-900">Find compatible pairs</div>
                      <div className="text-xs text-gray-500">Check all constraints between every two orders</div>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <div className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-bold">3</div>
                    <div>
                      <div className="text-sm font-medium text-gray-900">Merge compatible orders</div>
                      <div className="text-xs text-gray-500">Orders join the smallest compatible bundle</div>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <div className="flex-shrink-0 w-6 h-6 rounded-full bg-green-100 text-green-600 flex items-center justify-center text-xs font-bold">✓</div>
                    <div>
                      <div className="text-sm font-medium text-gray-900">Repeat until stable</div>
                      <div className="text-xs text-gray-500">Stop when no more merges are possible</div>
                    </div>
                  </div>
                </div>

                {/* Constraints */}
                <h4 className="font-medium text-gray-900 mb-3">Bundling Constraints</h4>
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <Store className="h-4 w-4 text-gray-400" />
                      <span className="text-sm font-medium text-gray-900">Same Store</span>
                    </div>
                    <p className="text-xs text-gray-500">Orders from the same location</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span className="text-sm font-medium text-gray-900">Time Overlap</span>
                    </div>
                    <p className="text-xs text-gray-500">Delivery windows intersect</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <Package className="h-4 w-4 text-gray-400" />
                      <span className="text-sm font-medium text-gray-900">Inventory</span>
                    </div>
                    <p className="text-xs text-gray-500">Stock available for combined qty</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <Truck className="h-4 w-4 text-gray-400" />
                      <span className="text-sm font-medium text-gray-900">Capacity</span>
                    </div>
                    <p className="text-xs text-gray-500">Weight fits courier vehicle</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Active Bundles */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Truck className="h-5 w-5 text-green-600" />
              <h3 className="font-semibold text-gray-900">Active Bundles</h3>
            </div>
            <div className="flex items-center gap-4 text-sm text-gray-500">
              <span className="flex items-center gap-1">
                <span className="inline-block w-3 h-3 rounded-full bg-green-500"></span>
                {multiBundles.length} bundles ({multiBundles.reduce((sum, b) => sum + (b.bundle_size || 0), 0)} orders)
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block w-3 h-3 rounded-full bg-gray-300"></span>
                {singletonBundles.length} unbundled
              </span>
            </div>
          </div>
        </div>

        <div className="p-4">
          {bundles.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <ShoppingCart className="h-12 w-12 mx-auto mb-3 text-gray-300" />
              <p>No bundles yet. Create orders with overlapping delivery windows to see bundles form.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Multi-order bundles */}
              {Object.entries(bundlesByStore).map(([storeId, storeBundles]) => {
                const multiOrderBundles = storeBundles.filter((b) => (b.bundle_size || 0) > 1)
                if (multiOrderBundles.length === 0) return null

                const storeName = multiOrderBundles[0]?.store_name || storeId

                return (
                  <div key={storeId} className="border rounded-lg overflow-hidden">
                    <div className="bg-gray-50 px-4 py-2 border-b">
                      <div className="flex items-center gap-2">
                        <Store className="h-4 w-4 text-gray-500" />
                        <span className="font-medium text-gray-900">{storeName}</span>
                        <span className="text-xs text-gray-500">
                          ({multiOrderBundles.length} bundle{multiOrderBundles.length !== 1 ? 's' : ''})
                        </span>
                      </div>
                    </div>
                    <div className="divide-y">
                      {multiOrderBundles.map((bundle) => (
                        <div key={bundle.bundle_id} className="p-4">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-green-100 text-green-700 text-sm font-semibold">
                                {bundle.bundle_size}
                              </span>
                              <span className="text-sm text-gray-600">orders bundled</span>
                            </div>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {(bundle.orders || []).map((orderId) => (
                              <span
                                key={orderId}
                                className="inline-flex items-center px-2 py-1 rounded bg-green-50 text-green-700 text-xs font-mono"
                              >
                                {orderId.replace('order:', '')}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )
              })}

              {/* Singleton bundles (unbundled orders) */}
              {singletonBundles.length > 0 && (
                <div className="border rounded-lg overflow-hidden border-dashed">
                  <div className="bg-gray-50 px-4 py-2 border-b">
                    <div className="flex items-center gap-2">
                      <Package className="h-4 w-4 text-gray-400" />
                      <span className="font-medium text-gray-500">Unbundled Orders</span>
                      <span className="text-xs text-gray-400">
                        (no compatible pairs found)
                      </span>
                    </div>
                  </div>
                  <div className="p-4">
                    <div className="flex flex-wrap gap-2">
                      {singletonBundles.map((bundle) => (
                        <span
                          key={bundle.bundle_id}
                          className="inline-flex items-center px-2 py-1 rounded bg-gray-100 text-gray-600 text-xs font-mono"
                          title={`Store: ${bundle.store_name || bundle.store_id}`}
                        >
                          {bundle.bundle_id.replace('order:', '')}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
