import React from 'react'
import { Menu, X } from 'lucide-react'

interface NavbarProps {
  currentPage: string
  onPageChange: (page: string) => void
}

export const Navbar: React.FC<NavbarProps> = ({ currentPage, onPageChange }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false)

  const navItems = [
    { id: 'pipeline', label: '⚙️ Pipeline' },
    { id: 'analysis', label: '🔍 Analysis' },
    { id: 'dashboard', label: '📊 Dashboard' },
    { id: 'history', label: '📚 History' },
  ]

  const handleNavClick = (page: string) => {
    onPageChange(page)
    setMobileMenuOpen(false)
  }

  return (
    <nav className="bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="text-2xl font-bold">🤖 Agent Test</div>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex gap-1">
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => handleNavClick(item.id)}
                className={`px-4 py-2 rounded-lg font-medium text-sm transition-all ${
                  currentPage === item.id
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-700 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-gray-700 hover:bg-gray-100"
            >
              {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <div className="md:hidden pb-4 border-t border-gray-200">
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => handleNavClick(item.id)}
                className={`w-full text-left px-4 py-2 rounded-lg font-medium text-sm transition-all ${
                  currentPage === item.id
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-700 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </nav>
  )
}
