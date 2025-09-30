'use client'

import React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Button } from '@/components/ui/button'

const Navigation: React.FC = () => {
  const pathname = usePathname()

  const navItems = [
    { href: '/', label: '메인 대시보드', icon: '📊' },
    { href: '/chatbot-test', label: '챗봇 테스트', icon: '🤖' },
    { href: '/server-settings', label: '서버 설정', icon: '⚙️' }
  ]

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200 mb-8">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-8">
            <Link href="/" className="flex items-center space-x-2">
              <span className="text-2xl">🔒</span>
              <span className="text-xl font-bold text-gray-900">SDC Admin</span>
            </Link>
            
            <div className="flex space-x-1">
              {navItems.map((item) => (
                <Link key={item.href} href={item.href}>
                  <Button
                    variant={pathname === item.href ? "default" : "ghost"}
                    className="flex items-center space-x-2"
                  >
                    <span>{item.icon}</span>
                    <span>{item.label}</span>
                  </Button>
                </Link>
              ))}
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-500">
              Korean RAG Admin Panel
            </span>
          </div>
        </div>
      </div>
    </nav>
  )
}

export default Navigation