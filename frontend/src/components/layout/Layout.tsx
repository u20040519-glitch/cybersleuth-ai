// =============================================================================
// CYBERSLEUTH AI - Main Layout
// =============================================================================

import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { TopNav } from './TopNav'

export function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(true)

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar collapsed={!sidebarOpen} />
      <div className={`flex-1 flex flex-col overflow-hidden ${window.innerWidth < 768 ? 'lg:pl-0' : ''}`}>
        <TopNav sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="flex-1 overflow-y-auto p-4 lg:p-6 bg-background">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
