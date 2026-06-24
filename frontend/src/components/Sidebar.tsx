import React from 'react'

interface SidebarProps {
  isOpen: boolean
  setIsOpen: (open: boolean) => void
}

export default function Sidebar({ isOpen }: SidebarProps) {
  const menuItems = [
    { icon: '📊', label: 'Dashboard', href: '#' },
    { icon: '📝', label: 'Stories', href: '#' },
    { icon: '✅', label: 'Tests', href: '#' },
    { icon: '🐛', label: 'Issues', href: '#' },
    { icon: '📈', label: 'Analytics', href: '#' },
    { icon: '⚙️', label: 'Settings', href: '#' },
  ]

  return (
    <aside className={`${isOpen ? 'w-64' : 'w-20'} bg-gray-900 text-white transition-all duration-300 flex flex-col`}>
      <div className="p-4 flex items-center justify-center border-b border-gray-700">
        <span className={`${isOpen ? 'text-xl font-bold' : 'hidden'}`}>AT</span>
      </div>

      <nav className="flex-1 px-2 py-4 space-y-2">
        {menuItems.map((item) => (
          <a
            key={item.label}
            href={item.href}
            className="flex items-center space-x-3 px-3 py-2 rounded-lg hover:bg-gray-800 transition-colors"
          >
            <span className="text-lg">{item.icon}</span>
            {isOpen && <span className="text-sm font-medium">{item.label}</span>}
          </a>
        ))}
      </nav>

      <div className="p-4 border-t border-gray-700 text-xs text-gray-400">
        {isOpen && <p>© 2026 Sopra Steria</p>}
      </div>
    </aside>
  )
}
