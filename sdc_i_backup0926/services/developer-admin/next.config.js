const path = require('path')
const fs = require('fs')

// 메인 .env 파일 직접 읽기
let HOST_IP = '192.168.122.177'
try {
  const envPath = path.resolve(__dirname, '../../.env')
  const envFile = fs.readFileSync(envPath, 'utf8')
  const hostIpMatch = envFile.match(/HOST_IP=(.+)/)
  if (hostIpMatch) {
    HOST_IP = hostIpMatch[1].trim()
  }
} catch (error) {
  console.log('Using default HOST_IP:', HOST_IP)
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  trailingSlash: true,
  reactStrictMode: true,
  swcMinify: true,
  env: {
    HOST_IP: HOST_IP,
    NEXT_PUBLIC_HOST_IP: HOST_IP,
  },
}

module.exports = nextConfig