import { useQuery } from '@tanstack/react-query'
import { freshmartApi, OrderFlat } from '../api/client'
import { Package, Clock, CheckCircle, XCircle, Truck } from 'lucide-react'

const statusConfig: Record<string, { color: string; icon: typeof Package }> = {
  CREATED: { color: 'bg-blue-100 text-blue-800', icon: Package },
  PICKING: { color: 'bg-yellow-100 text-yellow-800', icon: Clock },
  OUT_FOR_DELIVERY: { color: 'bg-purple-100 text-purple-800', icon: Truck },
  DELIVERED: { color: 'bg-green-100 text-green-800', icon: CheckCircle },
  CANCELLED: { color: 'bg-red-100 text-red-800', icon: XCircle },
}

function StatusBadge({ status }: { status: string | null }) {
  const config = statusConfig[status || ''] || { color: 'bg-gray-100 text-gray-800', icon: Package }
  const Icon = config.icon
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${config.color}`}>
      <Icon className="h-3 w-3" />
      {status || 'Unknown'}
    </span>
  )
}

function OrderCard({ order }: { order: OrderFlat }) {
  return (
    <div className="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start mb-3">
        <div>
          <h3 className="font-semibold text-gray-900">{order.order_number}</h3>
          <p className="text-sm text-gray-500">{order.customer_name}</p>
        </div>
        <StatusBadge status={order.order_status} />
      </div>
      <div className="space-y-1 text-sm">
        <p className="text-gray-600">
          <span className="font-medium">Store:</span> {order.store_name || order.store_id}
        </p>
        <p className="text-gray-600">
          <span className="font-medium">Window:</span>{' '}
          {order.delivery_window_start?.slice(11, 16)} - {order.delivery_window_end?.slice(11, 16)}
        </p>
        <p className="text-gray-900 font-medium">
          ${order.order_total_amount?.toFixed(2)}
        </p>
      </div>
    </div>
  )
}

export default function OrdersDashboardPage() {
  const { data: orders, isLoading, error } = useQuery({
    queryKey: ['orders'],
    queryFn: () => freshmartApi.listOrders().then(r => r.data),
  })

  // Group orders by status
  const ordersByStatus = orders?.reduce((acc, order) => {
    const status = order.order_status || 'Unknown'
    if (!acc[status]) acc[status] = []
    acc[status].push(order)
    return acc
  }, {} as Record<string, OrderFlat[]>) || {}

  const statusOrder = ['CREATED', 'PICKING', 'OUT_FOR_DELIVERY', 'DELIVERED', 'CANCELLED']

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Orders Dashboard</h1>
        <p className="text-gray-600">Monitor and manage FreshMart orders</p>
      </div>

      {isLoading && (
        <div className="text-center py-8 text-gray-500">Loading orders...</div>
      )}

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-lg">
          Error loading orders. Make sure the API is running.
        </div>
      )}

      {orders && (
        <>
          {/* Stats */}
          <div className="grid grid-cols-5 gap-4 mb-6">
            {statusOrder.map(status => (
              <div key={status} className="bg-white rounded-lg shadow p-4">
                <div className="text-sm text-gray-500">{status.replace('_', ' ')}</div>
                <div className="text-2xl font-bold text-gray-900">
                  {ordersByStatus[status]?.length || 0}
                </div>
              </div>
            ))}
          </div>

          {/* Orders grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {orders.map(order => (
              <OrderCard key={order.order_id} order={order} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
