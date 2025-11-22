import { useQuery } from '@tanstack/react-query'
import { healthApi } from '../api/client'
import { CheckCircle, XCircle, Server, Database, Search } from 'lucide-react'

export default function SettingsPage() {
  const { data: health, error: healthError } = useQuery({
    queryKey: ['health'],
    queryFn: () => healthApi.check().then(r => r.data),
    retry: false,
  })

  const { data: ready, error: readyError } = useQuery({
    queryKey: ['ready'],
    queryFn: () => healthApi.ready().then(r => r.data),
    retry: false,
  })

  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8080'

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-600">System configuration and health status</p>
      </div>

      {/* Health Status */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="font-semibold text-lg mb-4">Service Health</h2>
        <div className="grid grid-cols-3 gap-4">
          <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg">
            <Server className="h-8 w-8 text-gray-400" />
            <div>
              <p className="font-medium">API Server</p>
              <div className="flex items-center gap-1 text-sm">
                {health && !healthError ? (
                  <>
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    <span className="text-green-600">Healthy</span>
                  </>
                ) : (
                  <>
                    <XCircle className="h-4 w-4 text-red-500" />
                    <span className="text-red-600">Unreachable</span>
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg">
            <Database className="h-8 w-8 text-gray-400" />
            <div>
              <p className="font-medium">Database</p>
              <div className="flex items-center gap-1 text-sm">
                {ready?.database === 'connected' ? (
                  <>
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    <span className="text-green-600">Connected</span>
                  </>
                ) : (
                  <>
                    <XCircle className="h-4 w-4 text-red-500" />
                    <span className="text-red-600">Disconnected</span>
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg">
            <Search className="h-8 w-8 text-gray-400" />
            <div>
              <p className="font-medium">OpenSearch</p>
              <div className="flex items-center gap-1 text-sm text-gray-500">
                See search-sync logs
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Configuration */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="font-semibold text-lg mb-4">Configuration</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">API URL</label>
            <input
              type="text"
              value={apiUrl}
              readOnly
              className="w-full px-3 py-2 bg-gray-50 border rounded-lg text-gray-600"
            />
            <p className="text-sm text-gray-500 mt-1">
              Set via VITE_API_URL environment variable
            </p>
          </div>

          <div className="pt-4 border-t">
            <h3 className="font-medium mb-2">Environment</h3>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="text-gray-500">Mode:</div>
              <div>{import.meta.env.MODE}</div>
              <div className="text-gray-500">Production:</div>
              <div>{import.meta.env.PROD ? 'Yes' : 'No'}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
