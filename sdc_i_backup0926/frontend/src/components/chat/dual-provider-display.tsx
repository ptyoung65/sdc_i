"use client"

import * as React from "react"
import { motion } from "framer-motion"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Bot, Brain, Zap } from "lucide-react"
import { Checkbox } from "@/components/ui/checkbox"

interface DualProviderDisplayProps {
  gptResponse?: string
  perplexityResponse?: string
  isLoading?: boolean
  className?: string
}

export function DualProviderDisplay({
  gptResponse,
  perplexityResponse,
  isLoading = false,
  className
}: DualProviderDisplayProps) {
  const [showGPT, setShowGPT] = React.useState(true)
  const [showPerplexity, setShowPerplexity] = React.useState(true)

  // 둘 다 체크 해제될 경우 방지
  const handleGPTChange = (checked: boolean) => {
    if (!checked && !showPerplexity) return // 둘 다 체크 해제 방지
    setShowGPT(checked)
  }

  const handlePerplexityChange = (checked: boolean) => {
    if (!checked && !showGPT) return // 둘 다 체크 해제 방지
    setShowPerplexity(checked)
  }

  // 그리드 클래스 동적 계산
  const getGridClass = () => {
    if (showGPT && showPerplexity) return "grid-cols-1 lg:grid-cols-2"
    return "grid-cols-1"
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* 제어 패널 */}
      <div className="flex items-center gap-6 p-4 bg-muted/50 rounded-lg border">
        <div className="text-sm font-medium">표시할 결과 선택:</div>
        <div className="flex items-center space-x-2">
          <Checkbox
            id="show-gpt"
            checked={showGPT}
            onCheckedChange={handleGPTChange}
          />
          <label
            htmlFor="show-gpt"
            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer flex items-center gap-1"
          >
            <Bot className="h-4 w-4 text-blue-500" />
            GPT 결과
          </label>
        </div>
        <div className="flex items-center space-x-2">
          <Checkbox
            id="show-perplexity"
            checked={showPerplexity}
            onCheckedChange={handlePerplexityChange}
          />
          <label
            htmlFor="show-perplexity"
            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer flex items-center gap-1"
          >
            <Brain className="h-4 w-4 text-purple-500" />
            Perplexity 결과
          </label>
        </div>
      </div>

      {/* 결과 표시 영역 */}
      <div className={`grid ${getGridClass()} gap-4 h-full`}>
        {/* GPT Results */}
        {showGPT && (
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2 }}
          >
            <Card className="flex flex-col h-full">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Bot className="h-5 w-5 text-blue-500" />
                    GPT 결과
                  </CardTitle>
                  <Badge variant="secondary" className="bg-blue-100 text-blue-700">
                    gpt-4o-mini
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="flex-1 p-0">
                <ScrollArea className="h-full max-h-[600px] px-4 pb-4">
                  {isLoading && !gptResponse ? (
                    <div className="flex items-center justify-center h-32">
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                        className="h-6 w-6 border-2 border-blue-500 border-t-transparent rounded-full"
                      />
                    </div>
                  ) : gptResponse ? (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3 }}
                      className="prose prose-sm max-w-none dark:prose-invert"
                    >
                      <div className="whitespace-pre-wrap text-sm leading-relaxed">
                        {gptResponse}
                      </div>
                    </motion.div>
                  ) : (
                    <div className="flex items-center justify-center h-32 text-muted-foreground">
                      <div className="text-center">
                        <Bot className="h-8 w-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">GPT 응답을 기다리는 중...</p>
                      </div>
                    </div>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Perplexity Results */}
        {showPerplexity && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ duration: 0.2 }}
          >
            <Card className="flex flex-col h-full">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Brain className="h-5 w-5 text-purple-500" />
                    Perplexity 결과
                  </CardTitle>
                  <Badge variant="secondary" className="bg-purple-100 text-purple-700">
                    sonar
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="flex-1 p-0">
                <ScrollArea className="h-full max-h-[600px] px-4 pb-4">
                  {isLoading && !perplexityResponse ? (
                    <div className="flex items-center justify-center h-32">
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                        className="h-6 w-6 border-2 border-purple-500 border-t-transparent rounded-full"
                      />
                    </div>
                  ) : perplexityResponse ? (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3, delay: 0.1 }}
                      className="prose prose-sm max-w-none dark:prose-invert"
                    >
                      <div className="whitespace-pre-wrap text-sm leading-relaxed">
                        {perplexityResponse}
                      </div>
                    </motion.div>
                  ) : (
                    <div className="flex items-center justify-center h-32 text-muted-foreground">
                      <div className="text-center">
                        <Brain className="h-8 w-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">Perplexity 응답을 기다리는 중...</p>
                      </div>
                    </div>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </div>
    </div>
  )
}