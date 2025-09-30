'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Separator } from '../components/ui/separator'
import { Progress } from '../components/ui/progress'
import {
  Code2,
  Database,
  Server,
  Monitor,
  Terminal,
  Activity,
  Play,
  Square,
  RefreshCw,
  Globe,
  Settings,
  BarChart3,
  Cpu,
  MemoryStick,
  Clock,
  Container,
  ExternalLink,
  CheckCircle,
  XCircle,
  AlertCircle,
  FileText,
  Bug,
  Calendar,
  Eye
} from 'lucide-react'

interface ServiceStatus {
  name: string
  port: number
  status: 'running' | 'stopped' | 'error'
  url?: string
  description?: string
}

interface SystemMetrics {
  containers: number
  uptime: string
  memory: { used: number, total: number, percentage: number }
  cpu: { percentage: number }
  activeConnections: number
}

interface ErrorLog {
  id: string
  filename: string
  date: string
  title: string
  type: 'network' | 'api' | 'system' | 'application'
  severity: 'high' | 'medium' | 'low'
  status: 'resolved' | 'investigating' | 'open'
  summary: string
  fullPath: string
}

export default function DeveloperAdminPage() {
  // 환경변수에서 HOST_IP 가져오기 (기본값: 192.168.122.177)
  const HOST_IP = process.env.NEXT_PUBLIC_HOST_IP || '192.168.122.177'

  const [services, setServices] = useState<ServiceStatus[]>([
    {
      name: 'VSCode Server',
      port: 8080,
      status: 'running',
      url: `http://${HOST_IP}:8080`,
      description: 'Web-based IDE for development'
    },
    {
      name: 'Frontend Dev Server',
      port: 3000,
      status: 'running',
      url: `http://${HOST_IP}:3000`,
      description: 'Next.js development server'
    },
    {
      name: 'Backend API',
      port: 8000,
      status: 'stopped',
      url: `http://${HOST_IP}:8000`,
      description: 'FastAPI backend service'
    },
    {
      name: 'Admin Panel',
      port: 3003,
      status: 'running',
      url: `http://${HOST_IP}:3003`,
      description: 'Administrative interface'
    },
    {
      name: 'PgAdmin',
      port: 5050,
      status: 'stopped',
      url: `http://${HOST_IP}:5050`,
      description: 'PostgreSQL management'
    }
  ])

  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics>({
    containers: 4,
    uptime: '2h 45m',
    memory: { used: 1.2, total: 8.0, percentage: 15 },
    cpu: { percentage: 12 },
    activeConnections: 3
  })

  const [errorLogs, setErrorLogs] = useState<ErrorLog[]>([
    {
      id: '2025-09-21_NETWORK_ERROR_FIX',
      filename: '2025-09-21_NETWORK_ERROR_FIX.md',
      date: '2025-09-21',
      title: 'NetworkError 오류 해결',
      type: 'network',
      severity: 'high',
      status: 'resolved',
      summary: 'getUserConversations API 호출 시 NetworkError - URL 이중 작성 문제 해결',
      fullPath: '/home/chatpro/sdc_i/error/2025-09-21_NETWORK_ERROR_FIX.md'
    }
  ])

  const [selectedErrorLog, setSelectedErrorLog] = useState<ErrorLog | null>(null)
  const [errorLogContent, setErrorLogContent] = useState<string>('')
  const [isLoadingErrorContent, setIsLoadingErrorContent] = useState(false)

  const checkServiceStatus = async (port: number): Promise<'running' | 'stopped' | 'error'> => {
    try {
      const response = await fetch(`http://${HOST_IP}:${port}`, {
        method: 'HEAD',
        mode: 'no-cors'
      })
      return 'running'
    } catch (error) {
      return 'stopped'
    }
  }

  const refreshServiceStatus = async () => {
    const updatedServices = await Promise.all(
      services.map(async (service) => ({
        ...service,
        status: await checkServiceStatus(service.port)
      }))
    )
    setServices(updatedServices)
  }

  const getStatusIcon = (status: 'running' | 'stopped' | 'error') => {
    switch (status) {
      case 'running':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'stopped':
        return <XCircle className="h-4 w-4 text-gray-400" />
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />
    }
  }

  const getStatusVariant = (status: 'running' | 'stopped' | 'error'): "default" | "secondary" | "destructive" => {
    switch (status) {
      case 'running':
        return 'default'
      case 'stopped':
        return 'secondary'
      case 'error':
        return 'destructive'
    }
  }

  const getSeverityColor = (severity: 'high' | 'medium' | 'low') => {
    switch (severity) {
      case 'high':
        return 'text-red-500 bg-red-50 border-red-200'
      case 'medium':
        return 'text-yellow-500 bg-yellow-50 border-yellow-200'
      case 'low':
        return 'text-green-500 bg-green-50 border-green-200'
    }
  }

  const getErrorTypeIcon = (type: 'network' | 'api' | 'system' | 'application') => {
    switch (type) {
      case 'network':
        return <Globe className="h-4 w-4" />
      case 'api':
        return <Server className="h-4 w-4" />
      case 'system':
        return <Monitor className="h-4 w-4" />
      case 'application':
        return <Bug className="h-4 w-4" />
    }
  }

  const loadErrorLogContent = async (errorLog: ErrorLog) => {
    setIsLoadingErrorContent(true)
    try {
      // 실제 구현에서는 파일을 읽어오는 API를 호출하거나
      // 브라우저에서 접근 가능한 방식으로 파일 내용을 불러와야 합니다.
      // 여기서는 시뮬레이션을 위해 기본 내용을 설정합니다.
      const content = `# ${errorLog.title}

**날짜**: ${errorLog.date}
**타입**: ${errorLog.type}
**심각도**: ${errorLog.severity}
**상태**: ${errorLog.status}

## 요약
${errorLog.summary}

## 상세 내용
이 오류는 ${errorLog.date}에 발생했으며, ${errorLog.type} 관련 문제입니다.

해결 방법과 자세한 내용은 원본 파일을 참조하세요:
${errorLog.fullPath}
      `
      setErrorLogContent(content)
    } catch (error) {
      setErrorLogContent('오류 로그를 불러올 수 없습니다.')
    } finally {
      setIsLoadingErrorContent(false)
    }
  }

  const runningServices = services.filter(s => s.status === 'running').length

  useEffect(() => {
    refreshServiceStatus()
    const interval = setInterval(refreshServiceStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="container mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Monitor className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                SDC Developer Admin
              </h1>
              <p className="text-gray-600 mt-1">
                Development Environment Control Center
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-sm text-gray-500">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4" />
              <span>{runningServices}/{services.length} services active</span>
            </div>
            <Separator orientation="vertical" className="h-4" />
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4" />
              <span>Uptime: {systemMetrics.uptime}</span>
            </div>
          </div>
        </div>

        {/* System Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card className="border-0 shadow-md">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Container className="h-4 w-4 text-blue-500" />
                <CardTitle className="text-sm font-medium text-gray-600">
                  Active Services
                </CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">
                {runningServices}
              </div>
              <p className="text-xs text-gray-500 mt-1">
                of {services.length} total
              </p>
            </CardContent>
          </Card>

          <Card className="border-0 shadow-md">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-green-500" />
                <CardTitle className="text-sm font-medium text-gray-600">
                  System Uptime
                </CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {systemMetrics.uptime}
              </div>
              <p className="text-xs text-gray-500 mt-1">
                since last restart
              </p>
            </CardContent>
          </Card>

          <Card className="border-0 shadow-md">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <MemoryStick className="h-4 w-4 text-orange-500" />
                <CardTitle className="text-sm font-medium text-gray-600">
                  Memory Usage
                </CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-orange-600">
                {systemMetrics.memory.used}GB
              </div>
              <Progress
                value={systemMetrics.memory.percentage}
                className="mt-2 h-2"
              />
              <p className="text-xs text-gray-500 mt-1">
                {systemMetrics.memory.percentage}% of {systemMetrics.memory.total}GB
              </p>
            </CardContent>
          </Card>

          <Card className="border-0 shadow-md">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Cpu className="h-4 w-4 text-purple-500" />
                <CardTitle className="text-sm font-medium text-gray-600">
                  CPU Usage
                </CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-purple-600">
                {systemMetrics.cpu.percentage}%
              </div>
              <Progress
                value={systemMetrics.cpu.percentage}
                className="mt-2 h-2"
              />
              <p className="text-xs text-gray-500 mt-1">
                4 cores available
              </p>
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="services" className="space-y-6">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="services" className="flex items-center gap-2">
              <Server className="h-4 w-4" />
              Services
            </TabsTrigger>
            <TabsTrigger value="containers" className="flex items-center gap-2">
              <Container className="h-4 w-4" />
              Containers
            </TabsTrigger>
            <TabsTrigger value="monitoring" className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              Monitoring
            </TabsTrigger>
            <TabsTrigger value="error-logs" className="flex items-center gap-2">
              <Bug className="h-4 w-4" />
              Error Logs
            </TabsTrigger>
            <TabsTrigger value="tools" className="flex items-center gap-2">
              <Settings className="h-4 w-4" />
              Tools
            </TabsTrigger>
          </TabsList>

          {/* Services Tab */}
          <TabsContent value="services">
            <Card className="border-0 shadow-md">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Development Services
                </CardTitle>
                <Button onClick={refreshServiceStatus} variant="outline" size="sm">
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Refresh
                </Button>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {services.map((service) => (
                    <div key={service.name} className="flex items-center justify-between p-4 border border-gray-100 rounded-lg bg-white hover:shadow-sm transition-shadow">
                      <div className="flex items-center gap-4">
                        {getStatusIcon(service.status)}
                        <div>
                          <h3 className="font-semibold text-gray-900">{service.name}</h3>
                          <p className="text-sm text-gray-500">
                            Port {service.port} • {service.description}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge variant={getStatusVariant(service.status)}>
                          {service.status}
                        </Badge>
                        {service.url && service.status === 'running' && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => window.open(service.url, '_blank')}
                            className="gap-2"
                          >
                            <ExternalLink className="h-3 w-3" />
                            Open
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Container Management Tab */}
          <TabsContent value="containers">
            <Card className="border-0 shadow-md">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Container className="h-5 w-5" />
                  Container Management
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex gap-3">
                  <Button variant="default" className="flex items-center gap-2">
                    <Play className="h-4 w-4" />
                    Start All Services
                  </Button>
                  <Button variant="outline" className="flex items-center gap-2">
                    <Square className="h-4 w-4" />
                    Stop All Services
                  </Button>
                  <Button variant="outline" className="flex items-center gap-2">
                    <RefreshCw className="h-4 w-4" />
                    Restart Environment
                  </Button>
                </div>

                <Separator />

                <div className="bg-gray-50 rounded-lg p-4">
                  <h4 className="font-semibold mb-3 flex items-center gap-2">
                    <Terminal className="h-4 w-4" />
                    Quick Commands
                  </h4>
                  <div className="bg-gray-900 text-green-400 p-4 rounded-md font-mono text-sm space-y-1">
                    <div className="text-gray-500"># Start development environment</div>
                    <div>$ ./dev-start.sh</div>
                    <div className="text-gray-500 mt-2"># Stop all services</div>
                    <div>$ ./dev-stop.sh</div>
                    <div className="text-gray-500 mt-2"># Check container status</div>
                    <div>$ podman ps -a</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Monitoring Tab */}
          <TabsContent value="monitoring">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="border-0 shadow-md">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="h-5 w-5" />
                    System Resources
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <div className="flex justify-between text-sm mb-2">
                      <span>Memory Usage</span>
                      <span>{systemMetrics.memory.percentage}%</span>
                    </div>
                    <Progress value={systemMetrics.memory.percentage} />
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-2">
                      <span>CPU Usage</span>
                      <span>{systemMetrics.cpu.percentage}%</span>
                    </div>
                    <Progress value={systemMetrics.cpu.percentage} />
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-2">
                      <span>Active Connections</span>
                      <span>{systemMetrics.activeConnections}</span>
                    </div>
                    <Progress value={(systemMetrics.activeConnections / 10) * 100} />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-0 shadow-md">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Terminal className="h-5 w-5" />
                    Recent Activity
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3 text-sm">
                    <div className="flex items-center gap-3 text-green-600">
                      <CheckCircle className="h-4 w-4" />
                      <span>VSCode Server started successfully</span>
                      <span className="text-gray-400 ml-auto">2m ago</span>
                    </div>
                    <div className="flex items-center gap-3 text-green-600">
                      <CheckCircle className="h-4 w-4" />
                      <span>Frontend development server ready</span>
                      <span className="text-gray-400 ml-auto">5m ago</span>
                    </div>
                    <div className="flex items-center gap-3 text-yellow-600">
                      <AlertCircle className="h-4 w-4" />
                      <span>Backend API connection timeout</span>
                      <span className="text-gray-400 ml-auto">12m ago</span>
                    </div>
                    <div className="flex items-center gap-3 text-green-600">
                      <CheckCircle className="h-4 w-4" />
                      <span>Admin panel deployed</span>
                      <span className="text-gray-400 ml-auto">1h ago</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Error Logs Tab */}
          <TabsContent value="error-logs">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Error Logs List */}
              <div className="lg:col-span-2">
                <Card className="border-0 shadow-md">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Bug className="h-5 w-5" />
                      Error Logs
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {errorLogs.map((errorLog) => (
                        <div
                          key={errorLog.id}
                          className="flex items-center justify-between p-4 border border-gray-100 rounded-lg bg-white hover:shadow-sm transition-shadow cursor-pointer"
                          onClick={() => {
                            setSelectedErrorLog(errorLog)
                            loadErrorLogContent(errorLog)
                          }}
                        >
                          <div className="flex items-center gap-4">
                            <div className="flex items-center gap-2">
                              {getErrorTypeIcon(errorLog.type)}
                              <div className={`px-2 py-1 rounded-md text-xs font-medium border ${getSeverityColor(errorLog.severity)}`}>
                                {errorLog.severity}
                              </div>
                            </div>
                            <div>
                              <h3 className="font-semibold text-gray-900">{errorLog.title}</h3>
                              <p className="text-sm text-gray-500">
                                {errorLog.date} • {errorLog.summary}
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-3">
                            <Badge variant={errorLog.status === 'resolved' ? 'default' : errorLog.status === 'investigating' ? 'secondary' : 'destructive'}>
                              {errorLog.status}
                            </Badge>
                            <Button variant="outline" size="sm">
                              <Eye className="h-3 w-3 mr-1" />
                              View
                            </Button>
                          </div>
                        </div>
                      ))}

                      {errorLogs.length === 0 && (
                        <div className="text-center py-8 text-gray-500">
                          <Bug className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                          <p>No error logs found</p>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Error Log Detail */}
              <div className="lg:col-span-1">
                <Card className="border-0 shadow-md">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <FileText className="h-5 w-5" />
                      Error Details
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {selectedErrorLog ? (
                      <div className="space-y-4">
                        <div>
                          <h3 className="font-semibold text-lg">{selectedErrorLog.title}</h3>
                          <div className="flex items-center gap-2 mt-2">
                            <Calendar className="h-4 w-4 text-gray-400" />
                            <span className="text-sm text-gray-600">{selectedErrorLog.date}</span>
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          {getErrorTypeIcon(selectedErrorLog.type)}
                          <span className="text-sm font-medium">{selectedErrorLog.type}</span>
                          <div className={`px-2 py-1 rounded-md text-xs font-medium border ${getSeverityColor(selectedErrorLog.severity)}`}>
                            {selectedErrorLog.severity}
                          </div>
                        </div>

                        <div>
                          <h4 className="font-medium mb-2">Summary</h4>
                          <p className="text-sm text-gray-600">{selectedErrorLog.summary}</p>
                        </div>

                        {isLoadingErrorContent ? (
                          <div className="text-center py-4">
                            <RefreshCw className="h-6 w-6 animate-spin mx-auto" />
                            <p className="text-sm text-gray-500 mt-2">Loading content...</p>
                          </div>
                        ) : errorLogContent && (
                          <div>
                            <h4 className="font-medium mb-2">Content Preview</h4>
                            <div className="bg-gray-50 p-3 rounded-lg text-xs text-gray-700 max-h-60 overflow-y-auto">
                              <pre className="whitespace-pre-wrap">{errorLogContent}</pre>
                            </div>
                          </div>
                        )}

                        <div className="pt-3 border-t">
                          <p className="text-xs text-gray-500">
                            File: {selectedErrorLog.filename}
                          </p>
                          <p className="text-xs text-gray-500">
                            Path: {selectedErrorLog.fullPath}
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center py-8 text-gray-500">
                        <FileText className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                        <p>Select an error log to view details</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          {/* Development Tools Tab */}
          <TabsContent value="tools">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="border-0 shadow-md">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Code2 className="h-5 w-5" />
                    Development Environment
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Button
                    variant="outline"
                    className="w-full justify-start h-12 gap-3"
                    onClick={() => window.open(`http://${HOST_IP}:8080`, '_blank')}
                  >
                    <div className="p-2 bg-blue-100 rounded-lg">
                      <Terminal className="h-4 w-4 text-blue-600" />
                    </div>
                    <div className="text-left">
                      <div className="font-medium">VSCode Web IDE</div>
                      <div className="text-xs text-gray-500">Password: sdc_dev_2025</div>
                    </div>
                    <ExternalLink className="h-4 w-4 ml-auto" />
                  </Button>

                  <Button
                    variant="outline"
                    className="w-full justify-start h-12 gap-3"
                    onClick={() => window.open(`http://${HOST_IP}:3000`, '_blank')}
                  >
                    <div className="p-2 bg-green-100 rounded-lg">
                      <Globe className="h-4 w-4 text-green-600" />
                    </div>
                    <div className="text-left">
                      <div className="font-medium">Frontend Application</div>
                      <div className="text-xs text-gray-500">Next.js development server</div>
                    </div>
                    <ExternalLink className="h-4 w-4 ml-auto" />
                  </Button>

                  <Button
                    variant="outline"
                    className="w-full justify-start h-12 gap-3"
                    onClick={() => window.open(`http://${HOST_IP}:8000/docs`, '_blank')}
                  >
                    <div className="p-2 bg-purple-100 rounded-lg">
                      <Server className="h-4 w-4 text-purple-600" />
                    </div>
                    <div className="text-left">
                      <div className="font-medium">Backend API Docs</div>
                      <div className="text-xs text-gray-500">FastAPI documentation</div>
                    </div>
                    <ExternalLink className="h-4 w-4 ml-auto" />
                  </Button>
                </CardContent>
              </Card>

              <Card className="border-0 shadow-md">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Database className="h-5 w-5" />
                    Database Tools
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Button
                    variant="outline"
                    className="w-full justify-start h-12 gap-3"
                    onClick={() => window.open(`http://${HOST_IP}:5050`, '_blank')}
                  >
                    <div className="p-2 bg-orange-100 rounded-lg">
                      <Database className="h-4 w-4 text-orange-600" />
                    </div>
                    <div className="text-left">
                      <div className="font-medium">PgAdmin</div>
                      <div className="text-xs text-gray-500">PostgreSQL management</div>
                    </div>
                    <ExternalLink className="h-4 w-4 ml-auto" />
                  </Button>

                  <div className="pt-3 border-t">
                    <div className="text-sm text-gray-600 mb-2">Connection Info:</div>
                    <div className="bg-gray-50 p-3 rounded-lg text-xs text-gray-500">
                      <div>PostgreSQL: {HOST_IP}:5433</div>
                      <div>Redis: {HOST_IP}:6379</div>
                      <div>User: sdc_dev_user</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}