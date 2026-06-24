import React from 'react'

interface KPICardProps {
  title: string
  value: string | number
  icon: string
  bgColor: string
  borderColor: string
}

export default function KPICard({ title, value, icon, bgColor, borderColor }: KPICardProps) {
  return (
    <div className={`kpi-card ${bgColor} border-2 ${borderColor}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-600 font-medium">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{value}</p>
        </div>
        <span className="text-3xl">{icon}</span>
      </div>
    </div>
  )
}
