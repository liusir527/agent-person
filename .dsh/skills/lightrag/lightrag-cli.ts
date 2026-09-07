#!/usr/bin/env node
/**
 * LightRAG CLI — thin wrapper around LightRagTool for skill usage.
 * Usage: npx tsx lightrag-cli.ts <command> [options]
 */

import { LightRagTool } from './lightRagTool.js'

type QueryMode = 'local' | 'global' | 'hybrid' | 'naive' | 'mix' | 'bypass'

function parseArgs(argv: string[]) {
  const args = argv.slice(2)
  let baseUrl = process.env.LIGHTRAG_URL || 'http://10.66.23.38:18080'
  let apiKey = process.env.LIGHTRAG_API_KEY
  let token = process.env.LIGHTRAG_TOKEN
  let command = ''
  const subArgs: string[] = []

  for (let i = 0; i < args.length; i++) {
    const a = args[i]
    if (a === '--url' && args[i + 1]) { baseUrl = args[++i]; continue }
    if (a === '--api-key' && args[i + 1]) { apiKey = args[++i]; continue }
    if (a === '--token' && args[i + 1]) { token = args[++i]; continue }
    if (a === '--help' || a === '-h') { command = 'help'; continue }
    if (!command && !a.startsWith('-')) { command = a; continue }
    subArgs.push(a)
  }

  if (!command) command = 'help'
  return { baseUrl, apiKey, token, command, subArgs }
}

function flag(argv: string[], name: string): string | undefined {
  const i = argv.indexOf(name)
  return i !== -1 && argv[i + 1] ? argv[i + 1] : undefined
}

function hasFlag(argv: string[], name: string): boolean {
  return argv.includes(name)
}

async function main() {
  const args = parseArgs(process.argv)
  const tool = new LightRagTool({ baseUrl: args.baseUrl, apiKey: args.apiKey })
  if (args.token) tool.setToken(args.token)

  try {
    switch (args.command) {
      case 'login': {
        const user = flag(args.subArgs, '--user') || flag(args.subArgs, '-u')
        const pass = flag(args.subArgs, '--pass') || flag(args.subArgs, '-p')
        if (!user || !pass) { console.error('Usage: login -u <user> -p <pass>'); process.exit(1) }
        const tok = await tool.login(user, pass)
        console.log(JSON.stringify({ access_token: tok }))
        break
      }

      case 'query': {
        const q = flag(args.subArgs, '--query') || flag(args.subArgs, '-q') || args.subArgs[0]
        if (!q) { console.error('Usage: query -q "<question>"'); process.exit(1) }
        const mode = (flag(args.subArgs, '--mode') || 'mix') as QueryMode
        const ctxOnly = hasFlag(args.subArgs, '--context-only')
        const result = await tool.query({ query: q, mode, only_need_context: ctxOnly })
        console.log(JSON.stringify(result, null, 2))
        break
      }

      case 'query-data': {
        const q = flag(args.subArgs, '--query') || flag(args.subArgs, '-q') || args.subArgs[0]
        if (!q) { console.error('Usage: query-data -q "<question>"'); process.exit(1) }
        const mode = (flag(args.subArgs, '--mode') || 'mix') as QueryMode
        const result = await tool.queryWithData({ query: q, mode })
        console.log(JSON.stringify(result, null, 2))
        break
      }

      case 'insert': {
        const text = flag(args.subArgs, '--text') || flag(args.subArgs, '-t') || args.subArgs[0]
        if (!text) { console.error('Usage: insert -t "<text>"'); process.exit(1) }
        const source = flag(args.subArgs, '--source')
        const result = await tool.insertText(text, source)
        console.log(JSON.stringify(result, null, 2))
        break
      }

      case 'insert-file': {
        const filePath = flag(args.subArgs, '--file') || flag(args.subArgs, '-f') || args.subArgs[0]
        if (!filePath) { console.error('Usage: insert-file -f <path>'); process.exit(1) }
        const fs = await import('fs')
        const path = await import('path')
        const content = fs.readFileSync(filePath, 'utf-8')
        const filename = path.basename(filePath)
        const blob = new Blob([content])
        const result = await tool.uploadFile(blob, filename)
        console.log(JSON.stringify(result, null, 2))
        break
      }

      case 'docs': {
        const page = parseInt(flag(args.subArgs, '--page') || '1')
        const pageSize = parseInt(flag(args.subArgs, '--page-size') || '20')
        const status = flag(args.subArgs, '--status') as any
        const result = await tool.listDocuments({ page, page_size: pageSize, status_filter: status })
        console.log(JSON.stringify(result, null, 2))
        break
      }

      case 'status-counts': {
        const result = await tool.getStatusCounts()
        console.log(JSON.stringify(result, null, 2))
        break
      }

      case 'pipeline-status': {
        const result = await tool.getPipelineStatus()
        console.log(JSON.stringify(result, null, 2))
        break
      }

      case 'track': {
        const trackId = args.subArgs[0]
        if (!trackId) { console.error('Usage: track <track-id>'); process.exit(1) }
        const result = await tool.trackStatus(trackId)
        console.log(JSON.stringify(result, null, 2))
        break
      }

      case 'delete': {
        const ids = flag(args.subArgs, '--ids')
        if (!ids) { console.error('Usage: delete --ids id1,id2,id3'); process.exit(1) }
        const result = await tool.deleteDocuments({ doc_ids: ids.split(',') })
        console.log(JSON.stringify(result, null, 2))
        break
      }

      case 'clear': {
        const result = await tool.clearAllDocuments()
        console.log(JSON.stringify(result, null, 2))
        break
      }

      case 'clear-cache': {
        const result = await tool.clearCache()
        console.log(JSON.stringify(result, null, 2))
        break
      }

      case 'scan': {
        const result = await tool.scanForNewDocuments()
        console.log(JSON.stringify(result, null, 2))
        break
      }

      case 'reprocess': {
        const result = await tool.reprocessFailed()
        console.log(JSON.stringify(result, null, 2))
        break
      }

      case 'cancel': {
        const result = await tool.cancelPipeline()
        console.log(JSON.stringify(result, null, 2))
        break
      }

      case 'delete-entity': {
        const name = flag(args.subArgs, '--name') || args.subArgs[0]
        if (!name) { console.error('Usage: delete-entity --name <name>'); process.exit(1) }
        const result = await tool.deleteEntity(name)
        console.log(JSON.stringify(result, null, 2))
        break
      }

      case 'delete-relation': {
        const src = flag(args.subArgs, '--src') || args.subArgs[0]
        const tgt = flag(args.subArgs, '--tgt') || args.subArgs[1]
        if (!src || !tgt) { console.error('Usage: delete-relation --src <src> --tgt <tgt>'); process.exit(1) }
        const result = await tool.deleteRelation(src, tgt)
        console.log(JSON.stringify(result, null, 2))
        break
      }

      case 'help':
      default:
        console.log(`LightRAG CLI

Usage: npx tsx lightrag-cli.ts <command> [options]

Global options:
  --url <url>        LightRAG server URL (default: $LIGHTRAG_URL or http://10.66.23.38:18080)
  --api-key <key>    API key (default: $LIGHTRAG_API_KEY)
  --token <token>    Bearer token (default: $LIGHTRAG_TOKEN)

Auth:
  login -u <user> -p <pass>

Query:
  query -q "<question>" [--mode mix|local|global|hybrid|naive|bypass] [--context-only]
  query-data -q "<question>" [--mode mix]

Insert:
  insert -t "<text>" [--source <file-source>]
  insert-file -f <path>

Documents:
  docs [--page N] [--page-size N] [--status pending|processing|processed|failed]
  status-counts
  pipeline-status
  track <track-id>

Management:
  delete --ids id1,id2,id3
  clear
  clear-cache
  scan
  reprocess
  cancel
  delete-entity --name <entity-name>
  delete-relation --src <source> --tgt <target>`)
    }
  } catch (err: any) {
    console.error(`Error: ${err.message}`)
    process.exit(1)
  }
}

main()
