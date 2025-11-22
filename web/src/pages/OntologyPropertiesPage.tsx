import { useQuery } from '@tanstack/react-query'
import { ontologyApi } from '../api/client'
import { ArrowRight } from 'lucide-react'

export default function OntologyPropertiesPage() {
  const { data: properties, isLoading, error } = useQuery({
    queryKey: ['ontology-properties'],
    queryFn: () => ontologyApi.listProperties().then(r => r.data),
  })

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Ontology Properties</h1>
        <p className="text-gray-600">Define relationships and attributes for entity classes</p>
      </div>

      {isLoading && <div className="text-center py-8 text-gray-500">Loading...</div>}
      {error && <div className="bg-red-50 text-red-700 p-4 rounded-lg">Error loading properties</div>}

      {properties && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Property</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Domain</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Range</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Flags</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Description</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {properties.map(prop => (
                <tr key={prop.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <code className="text-sm font-medium text-blue-600">{prop.prop_name}</code>
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-1 text-sm">
                      <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded">
                        {prop.domain_class_name}
                      </span>
                      <ArrowRight className="h-4 w-4 text-gray-400" />
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {prop.range_class_name ? (
                      <span className="bg-purple-100 text-purple-700 px-2 py-0.5 rounded text-sm">
                        {prop.range_class_name}
                      </span>
                    ) : (
                      <span className="bg-gray-100 text-gray-700 px-2 py-0.5 rounded text-sm">
                        {prop.range_kind}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                      {prop.is_required && (
                        <span className="text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded">required</span>
                      )}
                      {prop.is_multi_valued && (
                        <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">multi</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600 max-w-xs truncate">
                    {prop.description || '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
