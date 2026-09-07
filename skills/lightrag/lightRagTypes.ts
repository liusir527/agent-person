// LightRAG API Types

export interface LightRagConfig {
  baseUrl: string
  apiKey?: string
  username?: string
  password?: string
}

export type DocStatus = 'pending' | 'processing' | 'preprocessed' | 'processed' | 'failed'

export type QueryMode = 'local' | 'global' | 'hybrid' | 'naive' | 'mix' | 'bypass'

export interface QueryRequest {
  query: string
  mode?: QueryMode
  only_need_context?: boolean
  only_need_prompt?: boolean
  response_type?: string
  top_k?: number
  chunk_top_k?: number
  max_entity_tokens?: number
  max_relation_tokens?: number
  max_total_tokens?: number
  hl_keywords?: string[]
  ll_keywords?: string[]
  conversation_history?: Array<{ role: string; content: string }>
  user_prompt?: string
  enable_rerank?: boolean
  include_references?: boolean
  include_chunk_content?: boolean
  stream?: boolean
}

export interface ReferenceItem {
  reference_id: string
  file_path: string
  content?: string[]
}

export interface QueryResponse {
  response: string
  references?: ReferenceItem[]
}

export interface QueryDataResponse {
  status: string
  message: string
  data: {
    entities: Entity[]
    relationships: Relationship[]
    chunks: Chunk[]
    references: ReferenceItem[]
  }
  metadata: {
    query_mode: string
    keywords: {
      high_level: string[]
      low_level: string[]
    }
    processing_info?: {
      total_entities_found: number
      total_relations_found: number
      entities_after_truncation: number
      relations_after_truncation: number
      final_chunks_count: number
    }
  }
}

export interface Entity {
  entity_name: string
  entity_type: string
  description: string
  source_id: string
  file_path?: string
  reference_id?: string
}

export interface Relationship {
  src_id: string
  tgt_id: string
  description: string
  keywords: string
  weight: number
  source_id: string
  file_path?: string
  reference_id?: string
}

export interface Chunk {
  content: string
  file_path: string
  chunk_id: string
  reference_id?: string
}

export interface DocumentStatus {
  id: string
  content_summary: string
  content_length: number
  status: DocStatus
  created_at: string
  updated_at: string
  track_id?: string
  chunks_count?: number
  error_msg?: string
  metadata?: Record<string, unknown>
  file_path: string
}

export interface PaginationInfo {
  page: number
  page_size: number
  total_count: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}

export interface PaginatedDocsResponse {
  documents: DocumentStatus[]
  pagination: PaginationInfo
  status_counts: Record<string, number>
}

export interface InsertResponse {
  status: 'success' | 'duplicated' | 'partial_success' | 'failure'
  message: string
  track_id: string
}

export interface TrackStatusResponse {
  track_id: string
  documents: DocumentStatus[]
  total_count: number
  status_summary: Record<string, number>
}

export interface PipelineStatusResponse {
  autoscanned: boolean
  busy: boolean
  job_name: string
  job_start?: string
  docs: number
  batchs: number
  cur_batch: number
  request_pending: boolean
  latest_message: string
  history_messages?: string[]
  update_status?: Record<string, unknown>
}

export interface ClearDocumentsResponse {
  status: 'success' | 'partial_success' | 'busy' | 'fail'
  message: string
}

export interface DeleteDocRequest {
  doc_ids: string[]
  delete_file?: boolean
  delete_llm_cache?: boolean
}

export interface DeleteDocByIdResponse {
  status: 'deletion_started' | 'busy' | 'not_allowed'
  message: string
  doc_id: string
}

export interface DeletionResult {
  status: 'success' | 'not_found' | 'not_allowed' | 'fail'
  doc_id: string
  message: string
  status_code?: number
  file_path?: string | null
}

export interface StatusCountsResponse {
  status_counts: Record<string, number>
}

export interface ScanResponse {
  status: 'scanning_started'
  message?: string
  track_id: string
}

export interface ReprocessResponse {
  status: 'reprocessing_started'
  message: string
  track_id: string
}

export interface CancelPipelineResponse {
  status: 'cancellation_requested' | 'not_busy'
  message: string
}

export interface ClearCacheResponse {
  status: 'success' | 'fail'
  message: string
}

export interface InsertTextRequest {
  text: string
  file_source?: string
}

export interface InsertTextsRequest {
  texts: string[]
  file_sources?: string[]
}

export interface DocumentsRequest {
  status_filter?: DocStatus | null
  page?: number
  page_size?: number
  sort_field?: 'created_at' | 'updated_at' | 'id' | 'file_path'
  sort_direction?: 'asc' | 'desc'
}
