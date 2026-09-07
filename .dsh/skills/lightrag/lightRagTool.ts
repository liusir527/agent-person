import type {
  LightRagConfig,
  QueryRequest,
  QueryResponse,
  QueryDataResponse,
  QueryMode,
  InsertResponse,
  InsertTextRequest,
  InsertTextsRequest,
  PaginatedDocsResponse,
  DocumentsRequest,
  DocumentStatus,
  TrackStatusResponse,
  PipelineStatusResponse,
  ClearDocumentsResponse,
  DeleteDocRequest,
  DeleteDocByIdResponse,
  DeletionResult,
  StatusCountsResponse,
  ScanResponse,
  ReprocessResponse,
  CancelPipelineResponse,
  ClearCacheResponse,
} from './lightRagTypes'

export class LightRagTool {
  private baseUrl: string
  private apiKey?: string
  private token?: string

  constructor(config: LightRagConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, '')
    this.apiKey = config.apiKey
  }

  // ─── Auth ─────────────────────────────────────────────────────────────

  async login(username: string, password: string): Promise<string> {
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)
    formData.append('grant_type', 'password')

    const response = await fetch(`${this.baseUrl}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData.toString(),
    })

    if (!response.ok) {
      throw new Error(`Login failed: ${response.status} ${response.statusText}`)
    }

    const data = await response.json()
    this.token = data.access_token
    return data.access_token
  }

  setToken(token: string): void {
    this.token = token
  }

  // ─── Internal helpers ─────────────────────────────────────────────────

  private getHeaders(contentType?: string): Record<string, string> {
    const headers: Record<string, string> = {}

    if (contentType) {
      headers['Content-Type'] = contentType
    }

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    } else if (this.apiKey) {
      headers['X-API-Key'] = this.apiKey
    }

    return headers
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
    contentType?: string
  ): Promise<T> {
    const headers = this.getHeaders(contentType ?? (body !== undefined && typeof body !== "string" ? "application/json" : undefined))
    const options: RequestInit = { method, headers }

    if (body !== undefined) {
      options.body = typeof body === 'string' ? body : JSON.stringify(body)
    }

    const response = await fetch(`${this.baseUrl}${path}`, options)

    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Unknown error')
      throw new Error(`LightRAG API error ${response.status}: ${errorText}`)
    }

    return response.json()
  }

  // ─── Query API ────────────────────────────────────────────────────────

  async query(request: QueryRequest): Promise<QueryResponse> {
    return this.request<QueryResponse>('POST', '/query', request)
  }

  async queryWithContext(query: string, mode: QueryMode = 'mix'): Promise<QueryResponse> {
    return this.query({ query, mode, only_need_context: true })
  }

  async queryWithData(request: QueryRequest): Promise<QueryDataResponse> {
    return this.request<QueryDataResponse>('POST', '/query/data', request)
  }

  // ─── Documents API ────────────────────────────────────────────────────

  async listDocuments(request?: DocumentsRequest): Promise<PaginatedDocsResponse> {
    return this.request<PaginatedDocsResponse>('POST', '/documents/paginated', request ?? {})
  }

  async getStatusCounts(): Promise<StatusCountsResponse> {
    return this.request<StatusCountsResponse>('GET', '/documents/status_counts')
  }

  async getDocumentStatuses(): Promise<Record<string, DocumentStatus[]>> {
    const result = await this.request<{ statuses: Record<string, DocumentStatus[]> }>(
      'GET',
      '/documents'
    )
    return result.statuses
  }

  async uploadFile(file: Blob, filename: string): Promise<InsertResponse> {
    const formData = new FormData()
    formData.append('file', file, filename)

    const headers: Record<string, string> = {}
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    } else if (this.apiKey) {
      headers['X-API-Key'] = this.apiKey
    }

    const response = await fetch(`${this.baseUrl}/documents/upload`, {
      method: 'POST',
      headers,
      body: formData,
    })

    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Unknown error')
      throw new Error(`Upload failed ${response.status}: ${errorText}`)
    }

    return response.json()
  }

  async insertText(text: string, fileSource?: string): Promise<InsertResponse> {
    const body: InsertTextRequest = { text }
    if (fileSource !== undefined) {
      body.file_source = fileSource
    }
    return this.request<InsertResponse>('POST', '/documents/text', body)
  }

  async insertTexts(texts: string[], fileSources?: string[]): Promise<InsertResponse> {
    const body: InsertTextsRequest = { texts }
    if (fileSources !== undefined) {
      body.file_sources = fileSources
    }
    return this.request<InsertResponse>('POST', '/documents/texts', body)
  }

  async trackStatus(trackId: string): Promise<TrackStatusResponse> {
    return this.request<TrackStatusResponse>('GET', `/documents/track_status/${encodeURIComponent(trackId)}`)
  }

  async getPipelineStatus(): Promise<PipelineStatusResponse> {
    return this.request<PipelineStatusResponse>('GET', '/documents/pipeline_status')
  }

  async deleteDocuments(request: DeleteDocRequest): Promise<DeleteDocByIdResponse> {
    return this.request<DeleteDocByIdResponse>('DELETE', '/documents/delete_document', request)
  }

  async clearAllDocuments(): Promise<ClearDocumentsResponse> {
    return this.request<ClearDocumentsResponse>('DELETE', '/documents')
  }

  async clearCache(): Promise<ClearCacheResponse> {
    return this.request<ClearCacheResponse>('POST', '/documents/clear_cache', {})
  }

  async scanForNewDocuments(): Promise<ScanResponse> {
    return this.request<ScanResponse>('POST', '/documents/scan')
  }

  async reprocessFailed(): Promise<ReprocessResponse> {
    return this.request<ReprocessResponse>('POST', '/documents/reprocess_failed')
  }

  async cancelPipeline(): Promise<CancelPipelineResponse> {
    return this.request<CancelPipelineResponse>('POST', '/documents/cancel_pipeline')
  }

  async deleteEntity(entityName: string): Promise<DeletionResult> {
    return this.request<DeletionResult>('DELETE', '/documents/delete_entity', { entity_name: entityName })
  }

  async deleteRelation(sourceEntity: string, targetEntity: string): Promise<DeletionResult> {
    return this.request<DeletionResult>('DELETE', '/documents/delete_relation', {
      source_entity: sourceEntity,
      target_entity: targetEntity,
    })
  }
}

export default LightRagTool
