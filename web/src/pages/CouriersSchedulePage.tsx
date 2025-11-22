import { useQuery } from '@tanstack/react-query'
import { freshmartApi } from '../api/client'
import { Truck, Bike, Car, Coffee } from 'lucide-react'

const vehicleIcons: Record<string, typeof Truck> = {
  BIKE: Bike,
  CAR: Car,
  VAN: Truck,
}

const statusColors: Record<string, string> = {
  AVAILABLE: 'bg-green-100 text-green-800',
  ON_DELIVERY: 'bg-purple-100 text-purple-800',
  OFF_SHIFT: 'bg-gray-100 text-gray-800',
}

export default function CouriersSchedulePage() {
  const { data: couriers, isLoading, error } = useQuery({
    queryKey: ['couriers'],
    queryFn: () => freshmartApi.listCouriers().then(r => r.data),
  })

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Couriers & Schedule</h1>
        <p className="text-gray-600">View courier status and assigned tasks</p>
      </div>

      {isLoading && (
        <div className="text-center py-8 text-gray-500">Loading couriers...</div>
      )}

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-lg">
          Error loading couriers. Make sure the API is running.
        </div>
      )}

      {couriers && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {couriers.map(courier => {
            const VehicleIcon = vehicleIcons[courier.vehicle_type || ''] || Truck
            return (
              <div key={courier.courier_id} className="bg-white rounded-lg shadow p-4">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-100 rounded-lg">
                      <VehicleIcon className="h-5 w-5 text-blue-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">{courier.courier_name}</h3>
                      <p className="text-sm text-gray-500">{courier.vehicle_type}</p>
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    statusColors[courier.courier_status || ''] || 'bg-gray-100'
                  }`}>
                    {courier.courier_status?.replace('_', ' ')}
                  </span>
                </div>

                <div className="text-sm text-gray-600 mb-4">
                  <p>Home Store: {courier.home_store_id}</p>
                </div>

                {/* Tasks */}
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">
                    Assigned Tasks ({courier.tasks.length})
                  </h4>
                  {courier.tasks.length === 0 ? (
                    <div className="flex items-center gap-2 text-gray-500 text-sm">
                      <Coffee className="h-4 w-4" />
                      No active tasks
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {courier.tasks.map((task, idx) => (
                        <div
                          key={task.task_id || idx}
                          className="bg-gray-50 rounded p-2 text-sm"
                        >
                          <div className="flex justify-between">
                            <span className="font-medium">{task.order_id}</span>
                            <span className={`text-xs px-1.5 py-0.5 rounded ${
                              task.task_status === 'IN_PROGRESS' ? 'bg-blue-100 text-blue-700' :
                              task.task_status === 'COMPLETED' ? 'bg-green-100 text-green-700' :
                              'bg-gray-100 text-gray-700'
                            }`}>
                              {task.task_status}
                            </span>
                          </div>
                          {task.eta && (
                            <p className="text-gray-500 text-xs mt-1">
                              ETA: {task.eta.slice(11, 16)}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
