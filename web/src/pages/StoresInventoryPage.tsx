import { useQuery } from '@tanstack/react-query'
import { freshmartApi } from '../api/client'
import { Warehouse, AlertTriangle } from 'lucide-react'

export default function StoresInventoryPage() {
  const { data: stores, isLoading, error } = useQuery({
    queryKey: ['stores'],
    queryFn: () => freshmartApi.listStores().then(r => r.data),
  })

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Stores & Inventory</h1>
        <p className="text-gray-600">Monitor store status and inventory levels</p>
      </div>

      {isLoading && (
        <div className="text-center py-8 text-gray-500">Loading stores...</div>
      )}

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-lg">
          Error loading stores. Make sure the API is running.
        </div>
      )}

      {stores && (
        <div className="space-y-6">
          {stores.map(store => (
            <div key={store.store_id} className="bg-white rounded-lg shadow">
              {/* Store header */}
              <div className="p-4 border-b flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-green-100 rounded-lg">
                    <Warehouse className="h-6 w-6 text-green-600" />
                  </div>
                  <div>
                    <h2 className="font-semibold text-gray-900">{store.store_name}</h2>
                    <p className="text-sm text-gray-500">{store.store_address}</p>
                  </div>
                </div>
                <div className="text-right">
                  <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                    store.store_status === 'OPEN' ? 'bg-green-100 text-green-800' :
                    store.store_status === 'LIMITED' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {store.store_status}
                  </span>
                  <p className="text-sm text-gray-500 mt-1">
                    Zone: {store.store_zone}
                  </p>
                </div>
              </div>

              {/* Inventory table */}
              <div className="p-4">
                <h3 className="font-medium text-gray-700 mb-3">Inventory</h3>
                {store.inventory_items.length === 0 ? (
                  <p className="text-gray-500 text-sm">No inventory data available</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-gray-500 border-b">
                          <th className="pb-2">Product</th>
                          <th className="pb-2">Stock Level</th>
                          <th className="pb-2">Replenishment ETA</th>
                        </tr>
                      </thead>
                      <tbody>
                        {store.inventory_items.map(item => (
                          <tr key={item.inventory_id} className="border-b last:border-0">
                            <td className="py-2">{item.product_id}</td>
                            <td className="py-2">
                              <span className={`flex items-center gap-1 ${
                                (item.stock_level || 0) < 10 ? 'text-red-600' : 'text-gray-900'
                              }`}>
                                {(item.stock_level || 0) < 10 && (
                                  <AlertTriangle className="h-4 w-4" />
                                )}
                                {item.stock_level}
                              </span>
                            </td>
                            <td className="py-2 text-gray-500">
                              {item.replenishment_eta || '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
