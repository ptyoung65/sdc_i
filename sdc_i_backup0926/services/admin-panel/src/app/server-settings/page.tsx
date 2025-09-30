'use client'

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

// Simplified Select components for this page
const SimpleSelect = ({ value, onValueChange, children, className }: {
  value: string;
  onValueChange: (value: string) => void;
  children: React.ReactNode;
  className?: string;
}) => (
  <select
    value={value}
    onChange={(e) => onValueChange(e.target.value)}
    className={`flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ${className || ''}`}
  >
    {children}
  </select>
);

const SimpleOption = ({ value, children }: { value: string; children: React.ReactNode }) => (
  <option value={value}>{children}</option>
);

// 환경변수에서 HOST_IP 가져오기 (기본값: localhost)
const HOST_IP = process.env.NEXT_PUBLIC_HOST_IP || 'localhost';

interface ServerConfig {
  // 임베딩 서버 설정
  embedding_servers: Array<{
    url: string;
    name: string;
    api_key: string;
    status: 'active' | 'inactive' | 'unknown';
    is_primary?: boolean;
  }>;
  // LLM 서버 설정
  llm_servers: Array<{
    url: string;
    name: string;
    model: string;
    api_key: string;
    status: 'active' | 'inactive' | 'unknown';
    is_primary?: boolean;
  }>;
  // 현재 설정
  current_config: {
    use_internal_servers: boolean;
    internal_mode: 'embedding' | 'llm' | 'hybrid';
    default_model: string;
    primary_embedding_server?: string;
    primary_llm_server?: string;
  };
}

export default function ServerSettingsPage() {
  const [config, setConfig] = useState<ServerConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', content: string } | null>(null);
  const [testingConnection, setTestingConnection] = useState<{ [key: string]: boolean }>({});
  const [testingAllServers, setTestingAllServers] = useState(false);

  // 초기 서버 설정 로드
  useEffect(() => {
    loadServerConfig();
  }, []);

  const loadServerConfig = async () => {
    try {
      setLoading(true);

      // 백엔드 API에서 설정 가져오기
      const response = await axios.get(`http://${HOST_IP}:8000/api/v1/internal-servers/config`);

      if (response.data.success && response.data.data) {
        setConfig(response.data.data);
        // 🚀 초기 로드 시 자동 테스트 제거 - 사용자가 수동으로 테스트하도록 변경
        return;
      }

      // API 호출 실패 시 기본값 사용
      const defaultConfig: ServerConfig = {
        embedding_servers: [
          {
            url: 'http://11.93.26.130:8080',
            name: 'sdcrpapoc1v',
            api_key: 'f2047419707b466d879db0bo9a358e91',
            status: 'unknown',
            is_primary: true
          },
          {
            url: 'http://11.93.26.43:8080',
            name: 'sdcaipocv2',
            api_key: '074892baa9a743bob1b17oao51d534ef',
            status: 'unknown',
            is_primary: false
          },
          {
            url: 'http://11.93.33.10:8080',
            name: 'mischataiapddvv',
            api_key: '7e71f89144674f95b2o8864191412519',
            status: 'unknown',
            is_primary: false
          }
        ],
        llm_servers: [
          {
            url: 'http://11.93.33.10:8080',
            name: 'mischataiapdvv',
            model: 'Qwen3-235B-A228-instruct-2507',
            api_key: '784813265d50dfebb42d0442d0o6be26b1',
            status: 'unknown',
            is_primary: true
          },
          {
            url: 'http://11.93.33.13:8080',
            name: 'mischataidbdvv',
            model: 'Qwen3-235B-A228-instruct-2507',
            api_key: 'o98108b8e26dfa8b7b0obdf822661ob',
            status: 'unknown',
            is_primary: false
          }
        ],
        current_config: {
          use_internal_servers: false,
          internal_mode: 'hybrid',
          default_model: 'Qwen3-235B-A228-instruct-2507',
          primary_embedding_server: 'http://11.93.26.130:8080',
          primary_llm_server: 'http://11.93.33.10:8080'
        }
      };

      setConfig(defaultConfig);

      // 🚀 기본 설정 로드 시에도 자동 테스트 제거
    } catch (error) {
      console.error('Failed to load server config:', error);
      setMessage({ type: 'error', content: '서버 설정을 불러오는데 실패했습니다.' });
    } finally {
      setLoading(false);
    }
  };

  const checkAllServerStatus = async (serverConfig: ServerConfig | null = null) => {
    const targetConfig = serverConfig || config;
    if (!targetConfig) return;

    try {
      setTestingAllServers(true);

      // 🚀 병렬 테스트로 변경 - 모든 서버를 동시에 테스트
      const embeddingTests = targetConfig.embedding_servers.map(server =>
        checkServerStatus(server.url, 'embedding')
      );

      const llmTests = targetConfig.llm_servers.map(server =>
        checkServerStatus(server.url, 'llm')
      );

      // 모든 테스트를 동시에 실행 - 최대 8초 내에 모든 테스트 완료
      await Promise.allSettled([...embeddingTests, ...llmTests]);

      setMessage({ type: 'success', content: '모든 서버 연결 테스트가 완료되었습니다.' });
    } catch (error) {
      console.error('Server testing failed:', error);
      setMessage({ type: 'error', content: '서버 테스트 중 오류가 발생했습니다.' });
    } finally {
      setTestingAllServers(false);
    }
  };

  const checkServerStatus = async (url: string, type: 'embedding' | 'llm') => {
    try {
      setTestingConnection(prev => ({ ...prev, [url]: true }));

      // 백엔드 API를 통한 연결 테스트
      const response = await axios.post(`http://${HOST_IP}:8000/api/v1/internal-servers/test`, {
        server_url: url,
        server_type: type
      }, {
        timeout: 8000, // 🚀 타임아웃을 15초에서 8초로 단축
        headers: { 'Content-Type': 'application/json' }
      });

      if (config && response.data.success) {
        const updatedConfig = { ...config };
        const testResult = response.data.data;
        if (type === 'embedding') {
          const server = updatedConfig.embedding_servers.find(s => s.url === url);
          if (server) server.status = testResult.success ? 'active' : 'inactive';
        } else {
          const server = updatedConfig.llm_servers.find(s => s.url === url);
          if (server) server.status = testResult.success ? 'active' : 'inactive';
        }
        setConfig(updatedConfig);
      }
    } catch (error) {
      console.error(`Failed to check ${type} server ${url}:`, error);
      if (config) {
        const updatedConfig = { ...config };
        if (type === 'embedding') {
          const server = updatedConfig.embedding_servers.find(s => s.url === url);
          if (server) server.status = 'inactive';
        } else {
          const server = updatedConfig.llm_servers.find(s => s.url === url);
          if (server) server.status = 'inactive';
        }
        setConfig(updatedConfig);
      }
    } finally {
      setTestingConnection(prev => ({ ...prev, [url]: false }));
    }
  };

  const updateServerConfig = (field: string, value: any) => {
    if (!config) return;

    setConfig({
      ...config,
      current_config: {
        ...config.current_config,
        [field]: value
      }
    });
  };

  const updateServerInfo = (serverType: 'embedding' | 'llm', index: number, field: string, value: string) => {
    if (!config) return;

    const updatedConfig = { ...config };
    if (serverType === 'embedding') {
      updatedConfig.embedding_servers[index] = {
        ...updatedConfig.embedding_servers[index],
        [field]: value
      };
    } else {
      updatedConfig.llm_servers[index] = {
        ...updatedConfig.llm_servers[index],
        [field]: value
      };
    }
    setConfig(updatedConfig);
  };

  const setPrimaryServer = (serverType: 'embedding' | 'llm', serverUrl: string) => {
    if (!config) return;

    const updatedConfig = { ...config };

    // 해당 타입의 모든 서버를 비기본으로 설정
    if (serverType === 'embedding') {
      updatedConfig.embedding_servers.forEach(server => {
        server.is_primary = server.url === serverUrl;
      });
      updatedConfig.current_config.primary_embedding_server = serverUrl;
    } else {
      updatedConfig.llm_servers.forEach(server => {
        server.is_primary = server.url === serverUrl;
      });
      updatedConfig.current_config.primary_llm_server = serverUrl;
    }

    setConfig(updatedConfig);
    setMessage({ type: 'success', content: `기본 ${serverType === 'embedding' ? '임베딩' : 'LLM'} 서버가 설정되었습니다.` });
  };

  const addServer = (serverType: 'embedding' | 'llm') => {
    if (!config) return;

    const updatedConfig = { ...config };
    if (serverType === 'embedding') {
      updatedConfig.embedding_servers.push({
        url: '',
        name: '새 임베딩 서버',
        api_key: '',
        status: 'unknown',
        is_primary: false
      });
    } else {
      updatedConfig.llm_servers.push({
        url: '',
        name: '새 LLM 서버',
        model: 'Qwen3-235B-A228-instruct-2507',
        api_key: '',
        status: 'unknown',
        is_primary: false
      });
    }
    setConfig(updatedConfig);
  };

  const removeServer = (serverType: 'embedding' | 'llm', index: number) => {
    if (!config) return;

    const updatedConfig = { ...config };
    if (serverType === 'embedding') {
      updatedConfig.embedding_servers.splice(index, 1);
    } else {
      updatedConfig.llm_servers.splice(index, 1);
    }
    setConfig(updatedConfig);
  };

  const saveConfiguration = async () => {
    if (!config) return;

    try {
      setSaving(true);

      // 백엔드 API에 설정 저장
      const response = await axios.post(`http://${HOST_IP}:8000/api/v1/internal-servers/config`, {
        embedding_servers: config.embedding_servers,
        llm_servers: config.llm_servers,
        current_config: {
          use_internal_servers: config.current_config.use_internal_servers,
          internal_mode: config.current_config.internal_mode,
          default_model: config.current_config.default_model,
          primary_embedding_server: config.current_config.primary_embedding_server,
          primary_llm_server: config.current_config.primary_llm_server
        }
      });

      if (response.data.success) {
        setMessage({ type: 'success', content: '서버 설정이 성공적으로 저장되었습니다.' });
      } else {
        setMessage({ type: 'error', content: '설정 저장에 실패했습니다.' });
      }
    } catch (error) {
      console.error('Failed to save server config:', error);
      setMessage({ type: 'error', content: '설정 저장 중 오류가 발생했습니다.' });
    } finally {
      setSaving(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <Badge className="bg-green-500 text-white">활성</Badge>;
      case 'inactive':
        return <Badge className="bg-red-500 text-white">비활성</Badge>;
      default:
        return <Badge className="bg-gray-500 text-white">알 수 없음</Badge>;
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-lg">서버 설정을 로드하는 중...</div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <Alert>
          <AlertDescription>서버 설정을 불러올 수 없습니다.</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 max-w-6xl">
      <div className="space-y-6">
        {/* 헤더 */}
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold">내부 서버 설정</h1>
            <p className="text-gray-600 mt-2">임베딩 서버와 LLM 서버의 설정을 관리합니다.</p>
          </div>
          <div className="flex space-x-3">
            <Button
              onClick={() => checkAllServerStatus()}
              disabled={testingAllServers || !config}
              variant="outline"
              className="flex items-center space-x-2"
            >
              {testingAllServers ? (
                <>
                  <span className="w-4 h-4 border-2 border-gray-300 border-t-blue-600 rounded-full animate-spin"></span>
                  <span>모든 서버 테스트 중...</span>
                </>
              ) : (
                <>
                  <span>🔍</span>
                  <span>모든 서버 연결 테스트</span>
                </>
              )}
            </Button>
            <Button onClick={loadServerConfig} variant="outline">
              🔄 새로고침
            </Button>
          </div>
        </div>

        {/* 메시지 표시 */}
        {message && (
          <Alert className={message.type === 'success' ? 'border-green-500' : 'border-red-500'}>
            <AlertDescription>{message.content}</AlertDescription>
          </Alert>
        )}

        {/* 전체 설정 */}
        <Card>
          <CardHeader>
            <CardTitle>전체 설정</CardTitle>
            <CardDescription>내부 서버 사용 및 모드 설정</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center space-x-2">
              <Switch
                checked={config.current_config.use_internal_servers}
                onCheckedChange={(checked) => updateServerConfig('use_internal_servers', checked)}
              />
              <Label>내부 서버 사용</Label>
            </div>

            <div className="space-y-2">
              <Label>내부 서버 모드</Label>
              <SimpleSelect
                value={config.current_config.internal_mode}
                onValueChange={(value) => updateServerConfig('internal_mode', value)}
              >
                <SimpleOption value="embedding">임베딩 서버만</SimpleOption>
                <SimpleOption value="llm">LLM 서버만</SimpleOption>
                <SimpleOption value="hybrid">하이브리드 (내부 + 외부)</SimpleOption>
              </SimpleSelect>
            </div>

            <div className="space-y-2">
              <Label>기본 모델</Label>
              <Input
                value={config.current_config.default_model}
                onChange={(e) => updateServerConfig('default_model', e.target.value)}
                placeholder="모델명 입력"
              />
            </div>

            <Separator />

            <div className="space-y-3">
              <Label className="text-base font-semibold">현재 기본 서버 설정</Label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-sm text-gray-600">기본 임베딩 서버</Label>
                  <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    {config.embedding_servers.find(s => s.is_primary) ? (
                      <div>
                        <div className="font-medium text-blue-800">
                          {config.embedding_servers.find(s => s.is_primary)?.name}
                        </div>
                        <div className="text-sm text-blue-600">
                          {config.embedding_servers.find(s => s.is_primary)?.url}
                        </div>
                      </div>
                    ) : (
                      <div className="text-gray-500">기본 서버가 설정되지 않음</div>
                    )}
                  </div>
                </div>
                <div className="space-y-2">
                  <Label className="text-sm text-gray-600">기본 LLM 서버</Label>
                  <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                    {config.llm_servers.find(s => s.is_primary) ? (
                      <div>
                        <div className="font-medium text-green-800">
                          {config.llm_servers.find(s => s.is_primary)?.name}
                        </div>
                        <div className="text-sm text-green-600">
                          {config.llm_servers.find(s => s.is_primary)?.url}
                        </div>
                        <div className="text-xs text-green-600">
                          모델: {config.llm_servers.find(s => s.is_primary)?.model}
                        </div>
                      </div>
                    ) : (
                      <div className="text-gray-500">기본 서버가 설정되지 않음</div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 서버 설정 탭 */}
        <Tabs defaultValue="embedding" className="space-y-4">
          <TabsList>
            <TabsTrigger value="embedding">임베딩 서버</TabsTrigger>
            <TabsTrigger value="llm">LLM 서버</TabsTrigger>
          </TabsList>

          {/* 임베딩 서버 설정 */}
          <TabsContent value="embedding">
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center">
                  <div>
                    <CardTitle>임베딩 서버 설정</CardTitle>
                    <CardDescription>BGE-M3 모델을 사용하는 임베딩 서버들</CardDescription>
                  </div>
                  <Button onClick={() => addServer('embedding')} size="sm">
                    + 서버 추가
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {config.embedding_servers.map((server, index) => (
                    <div key={index} className={`border rounded-lg p-4 space-y-4 ${server.is_primary ? 'border-blue-500 bg-blue-50' : ''}`}>
                      {/* 서버 이름 및 기본 서버 표시 */}
                      <div className="flex justify-between items-center">
                        <div className="flex items-center space-x-3">
                          <Input
                            value={server.name}
                            onChange={(e) => updateServerInfo('embedding', index, 'name', e.target.value)}
                            className="font-semibold max-w-xs"
                            placeholder="서버 이름"
                          />
                          {server.is_primary && (
                            <Badge className="bg-blue-500 text-white">✓ 기본 서버</Badge>
                          )}
                        </div>
                        <div className="flex items-center space-x-2">
                          {getStatusBadge(server.status)}
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => removeServer('embedding', index)}
                            disabled={config.embedding_servers.length <= 1}
                          >
                            삭제
                          </Button>
                        </div>
                      </div>

                      {/* 기본 서버 설정 및 테스트 버튼 */}
                      <div className="flex justify-center space-x-3">
                        <Button
                          size="sm"
                          variant={server.is_primary ? "default" : "outline"}
                          onClick={() => setPrimaryServer('embedding', server.url)}
                          disabled={server.is_primary}
                          className="min-w-[120px]"
                        >
                          {server.is_primary ? '✓ 현재 기본 서버' : '🎯 기본으로 설정'}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => checkServerStatus(server.url, 'embedding')}
                          disabled={testingConnection[server.url]}
                          className="min-w-[100px]"
                        >
                          {testingConnection[server.url] ? '⏳ 테스트 중...' : '🔍 연결 테스트'}
                        </Button>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label>서버 URL</Label>
                          <Input
                            value={server.url}
                            onChange={(e) => updateServerInfo('embedding', index, 'url', e.target.value)}
                            placeholder="http://서버주소:포트"
                          />
                        </div>
                        <div>
                          <Label>API 키</Label>
                          <Input
                            type="password"
                            value={server.api_key}
                            onChange={(e) => updateServerInfo('embedding', index, 'api_key', e.target.value)}
                            placeholder="API 키 입력"
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* LLM 서버 설정 */}
          <TabsContent value="llm">
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center">
                  <div>
                    <CardTitle>LLM 서버 설정</CardTitle>
                    <CardDescription>Qwen3-235B 모델을 사용하는 LLM 서버들</CardDescription>
                  </div>
                  <Button onClick={() => addServer('llm')} size="sm">
                    + 서버 추가
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {config.llm_servers.map((server, index) => (
                    <div key={index} className={`border rounded-lg p-4 space-y-4 ${server.is_primary ? 'border-green-500 bg-green-50' : ''}`}>
                      {/* 서버 이름 및 기본 서버 표시 */}
                      <div className="flex justify-between items-center">
                        <div className="flex items-center space-x-3">
                          <Input
                            value={server.name}
                            onChange={(e) => updateServerInfo('llm', index, 'name', e.target.value)}
                            className="font-semibold max-w-xs"
                            placeholder="서버 이름"
                          />
                          {server.is_primary && (
                            <Badge className="bg-green-500 text-white">✓ 기본 서버</Badge>
                          )}
                        </div>
                        <div className="flex items-center space-x-2">
                          {getStatusBadge(server.status)}
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => removeServer('llm', index)}
                            disabled={config.llm_servers.length <= 1}
                          >
                            삭제
                          </Button>
                        </div>
                      </div>

                      {/* 기본 서버 설정 및 테스트 버튼 */}
                      <div className="flex justify-center space-x-3">
                        <Button
                          size="sm"
                          variant={server.is_primary ? "default" : "outline"}
                          onClick={() => setPrimaryServer('llm', server.url)}
                          disabled={server.is_primary}
                          className="min-w-[120px]"
                        >
                          {server.is_primary ? '✓ 현재 기본 서버' : '🎯 기본으로 설정'}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => checkServerStatus(server.url, 'llm')}
                          disabled={testingConnection[server.url]}
                          className="min-w-[100px]"
                        >
                          {testingConnection[server.url] ? '⏳ 테스트 중...' : '🔍 연결 테스트'}
                        </Button>
                      </div>

                      <div className="grid grid-cols-3 gap-4">
                        <div>
                          <Label>서버 URL</Label>
                          <Input
                            value={server.url}
                            onChange={(e) => updateServerInfo('llm', index, 'url', e.target.value)}
                            placeholder="http://서버주소:포트"
                          />
                        </div>
                        <div>
                          <Label>모델명</Label>
                          <Input
                            value={server.model}
                            onChange={(e) => updateServerInfo('llm', index, 'model', e.target.value)}
                            placeholder="모델명 입력"
                          />
                        </div>
                        <div>
                          <Label>API 키</Label>
                          <Input
                            type="password"
                            value={server.api_key}
                            onChange={(e) => updateServerInfo('llm', index, 'api_key', e.target.value)}
                            placeholder="API 키 입력"
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* 저장 버튼 */}
        <div className="flex justify-end space-x-4">
          <Button variant="outline" onClick={loadServerConfig}>
            초기화
          </Button>
          <Button onClick={saveConfiguration} disabled={saving}>
            {saving ? '저장 중...' : '설정 저장'}
          </Button>
        </div>
      </div>
    </div>
  );
}