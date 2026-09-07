import { describe, it, expect, vi, beforeEach } from "vitest"
import { LightRagTool } from "./lightRagTool"

const mockFetch = vi.fn()
vi.stubGlobal("fetch", mockFetch)

function mockJsonResponse(data: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "Error",
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  }
}

describe("LightRagTool", () => {
  let tool: LightRagTool

  beforeEach(() => {
    vi.clearAllMocks()
    tool = new LightRagTool({ baseUrl: "http://localhost:9621" })
  })

  describe("constructor", () => {
    it("trims trailing slash from baseUrl", async () => {
      const t = new LightRagTool({ baseUrl: "http://localhost:9621/" })
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ response: "ok" }))
      await t.query({ query: "test" })
      expect(mockFetch).toHaveBeenCalledWith("http://localhost:9621/query", expect.anything())
    })

    it("stores apiKey for header injection", async () => {
      const t = new LightRagTool({ baseUrl: "http://localhost:9621", apiKey: "my-key" })
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ response: "ok" }))
      await t.query({ query: "test" })
      const headers = mockFetch.mock.calls[0][1].headers
      expect(headers["X-API-Key"]).toBe("my-key")
    })
  })

  describe("login", () => {
    it("sends form-encoded credentials and stores token", async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ access_token: "tok-abc" }))
      const token = await tool.login("user", "pass")
      expect(token).toBe("tok-abc")
    })

    it("throws on login failure", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false, status: 401, statusText: "Unauthorized",
        text: () => Promise.resolve("bad credentials"),
      })
      await expect(tool.login("x", "y")).rejects.toThrow("Login failed: 401")
    })
  })

  describe("setToken", () => {
    it("sets token used in subsequent requests", async () => {
      tool.setToken("my-token")
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ response: "ok" }))
      await tool.query({ query: "test" })
      const headers = mockFetch.mock.calls[0][1].headers
      expect(headers["Authorization"]).toBe("Bearer my-token")
    })
  })

  describe("query", () => {
    it("POSTs to /query with body", async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ response: "answer" }))
      const result = await tool.query({ query: "what is X?", mode: "hybrid" })
      expect(result).toEqual({ response: "answer" })
    })
  })

  describe("queryWithContext", () => {
    it("defaults mode to mix and sets only_need_context", async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ response: "ctx" }))
      await tool.queryWithContext("hello")
      const body = JSON.parse(mockFetch.mock.calls[0][1].body)
      expect(body).toEqual({ query: "hello", mode: "mix", only_need_context: true })
    })

    it("accepts custom mode", async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ response: "ctx" }))
      await tool.queryWithContext("hello", "global")
      const body = JSON.parse(mockFetch.mock.calls[0][1].body)
      expect(body.mode).toBe("global")
    })
  })

  describe("queryWithData", () => {
    it("POSTs to /query/data", async () => {
      const dataResp = {
        status: "ok", message: "",
        data: { entities: [], relationships: [], chunks: [], references: [] },
        metadata: { query_mode: "mix", keywords: { high_level: [], low_level: [] } },
      }
      mockFetch.mockResolvedValueOnce(mockJsonResponse(dataResp))
      const result = await tool.queryWithData({ query: "detail" })
      expect(result.status).toBe("ok")
    })
  })

  describe("listDocuments", () => {
    it("POSTs to /documents/paginated with default empty body", async () => {
      const docsResp = {
        documents: [],
        pagination: { page: 1, page_size: 10, total_count: 0, total_pages: 0, has_next: false, has_prev: false },
        status_counts: {},
      }
      mockFetch.mockResolvedValueOnce(mockJsonResponse(docsResp))
      const result = await tool.listDocuments()
      expect(result.documents).toEqual([])
    })

    it("passes request params", async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse({
        documents: [],
        pagination: { page: 2, page_size: 5, total_count: 0, total_pages: 0, has_next: false, has_prev: true },
        status_counts: {},
      }))
      await tool.listDocuments({ page: 2, page_size: 5, status_filter: "processed" })
      const body = JSON.parse(mockFetch.mock.calls[0][1].body)
      expect(body).toEqual({ page: 2, page_size: 5, status_filter: "processed" })
    })
  })

  describe("getStatusCounts", () => {
    it("GETs /documents/status_counts", async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ status_counts: { processed: 5, pending: 2 } }))
      const result = await tool.getStatusCounts()
      expect(result.status_counts.processed).toBe(5)
    })
  })

  describe("getDocumentStatuses", () => {
    it("GETs /documents and returns statuses object", async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ statuses: { doc1: [{ id: "1", status: "processed" }] } }))
      const result = await tool.getDocumentStatuses()
      expect(result.doc1[0].status).toBe("processed")
    })
  })

  describe("uploadFile", () => {
    it("POSTs FormData to /documents/upload", async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ status: "success", message: "ok", track_id: "trk-1" }))
      const blob = new Blob(["hello"])
      const result = await tool.uploadFile(blob, "test.txt")
      expect(result.track_id).toBe("trk-1")
    })

    it("includes auth header when token is set", async () => {
      tool.setToken("tok-123")
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ status: "success", message: "", track_id: "t" }))
      await tool.uploadFile(new Blob(["x"]), "f.txt")
      const headers = mockFetch.mock.calls[0][1].headers
      expect(headers["Authorization"]).toBe("Bearer tok-123")
    })

    it("includes apiKey header when no token is set", async () => {
      const t = new LightRagTool({ baseUrl: "http://localhost:9621", apiKey: "api-key-1" })
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ status: "success", message: "", track_id: "t" }))
      await t.uploadFile(new Blob(["x"]), "f.txt")
      const headers = mockFetch.mock.calls[0][1].headers
      expect(headers["X-API-Key"]).toBe("api-key-1")
      expect(headers["Authorization"]).toBeUndefined()
    })
  })

  describe("insertText", () => {
    it("POSTs text to /documents/text", async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ status: "success", message: "", track_id: "t1" }))
      const result = await tool.insertText("some content", "source.txt")
      expect(result.status).toBe("success")
      const body = JSON.parse(mockFetch.mock.calls[0][1].body)
      expect(body).toEqual({ text: "some content", file_source: "source.txt" })
    })

    it("omits file_source when not provided", async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ status: "success", message: "", track_id: "t2" }))
      await tool.insertText("content only")
      const body = JSON.parse(mockFetch.mock.calls[0][1].body)
      expect(body).toEqual({ text: "content only" })
      expect(body.file_source).toBeUndefined()
    })
  })

  describe("insertTexts", () => {
    it("POSTs multiple texts to /documents/texts", async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ status: "success", message: "", track_id: "t3" }))
      await tool.insertTexts(["a", "b"], ["src-a", "src-b"])
      const body = JSON.parse(mockFetch.mock.calls[0][1].body)
      expect(body.texts).toEqual(["a", "b"])
      expect(body.file_sources).toEqual(["src-a", "src-b"])
    })
  })

  describe("trackStatus", () => {
    it("GETs /documents/track_status/:trackId", async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ track_id: "trk-1", documents: [], total_count: 0, status_summary: {} }))
      await tool.trackStatus("trk-1")
      expect(mockFetch).toHaveBeenCalledWith("http://localhost:9621/documents/track_status/trk-1", expect.objectContaining({ method: "GET" }))
    })

    it("encodes special characters in trackId", async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ track_id: "a/b", documents: [], total_count: 0, status_summary: {} }))
      await tool.trackStatus("a/b")
      expect(mockFetch).toHaveBeenCalledWith("http://localhost:9621/documents/track_status/a%2Fb", expect.anything())
    })
  })

  describe("getPipelineStatus", () => {
    it("GETs /documents/pipeline_status", async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse({
        autoscanned: false, busy: false, job_name: "default",
        docs: 0, batchs: 0, cur_batch: 0, request_pending: false, latest_message: "idle",
      }))
      const result = await tool.getPipelineStatus()
      expect(result.busy).toBe(false)
      expect(result.latest_message).toBe("idle")
    })
  })

  describe("deleteDocuments", () => {
    it("DELETEs /documents/delete_document with doc_ids", async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ status: "deletion_started", message: "", doc_id: "d1" }))
      const result = await tool.deleteDocuments({ doc_ids: ["d1", "d2"] })
      expect(result.status).toBe("deletion_started")
    })
  })

  describe("clearAllDocuments", () => {
    it("DELETEs /documents", async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ status: "success", message: "cleared" }))
      const result = await tool.clearAllDocuments()
      expect(result.status).toBe("success")
    })
  })

  describe("clearCache", () => {
    it("POSTs to /documents/clear_cache", async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ status: "success", message: "" }))
      const result = await tool.clearCache()
      expect(result.status).toBe("success")
    })
  })

  describe("scanForNewDocuments", () => {
    it("POSTs to /documents/scan", async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ status: "scanning_started", track_id: "scan-1" }))
      const result = await tool.scanForNewDocuments()
      expect(result.status).toBe("scanning_started")
      expect(result.track_id).toBe("scan-1")
    })
  })

  describe("reprocessFailed", () => {
    it("POSTs to /documents/reprocess_failed", async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ status: "reprocessing_started", message: "", track_id: "rp-1" }))
      const result = await tool.reprocessFailed()
      expect(result.status).toBe("reprocessing_started")
    })
  })

  describe("cancelPipeline", () => {
    it("POSTs to /documents/cancel_pipeline", async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ status: "cancellation_requested", message: "" }))
      const result = await tool.cancelPipeline()
      expect(result.status).toBe("cancellation_requested")
    })
  })

  describe("deleteEntity", () => {
    it("DELETEs /documents/delete_entity with entity_name", async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ status: "success", doc_id: "", message: "" }))
      await tool.deleteEntity("MyEntity")
      const body = JSON.parse(mockFetch.mock.calls[0][1].body)
      expect(body).toEqual({ entity_name: "MyEntity" })
    })
  })

  describe("deleteRelation", () => {
    it("DELETEs /documents/delete_relation with source and target", async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ status: "success", doc_id: "", message: "" }))
      await tool.deleteRelation("Src", "Tgt")
      const body = JSON.parse(mockFetch.mock.calls[0][1].body)
      expect(body).toEqual({ source_entity: "Src", target_entity: "Tgt" })
    })
  })

  describe("error handling", () => {
    it("throws with status code and error text on non-ok response", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false, status: 500, statusText: "Internal Server Error",
        text: () => Promise.resolve("something broke"),
      })
      await expect(tool.query({ query: "fail" })).rejects.toThrow("LightRAG API error 500: something broke")
    })

    it("uses fallback when error text read fails", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false, status: 502, statusText: "Bad Gateway",
        text: () => Promise.reject(new Error("broken")),
      })
      await expect(tool.query({ query: "fail" })).rejects.toThrow("LightRAG API error 502: Unknown error")
    })

    it("throws on upload failure", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false, status: 413, statusText: "Too Large",
        text: () => Promise.resolve("file too big"),
      })
      await expect(tool.uploadFile(new Blob(["x"]), "big.bin")).rejects.toThrow("Upload failed 413")
    })
  })

  describe("headers", () => {
    it("uses token over apiKey when both set", async () => {
      const t = new LightRagTool({ baseUrl: "http://localhost:9621", apiKey: "key" })
      t.setToken("tok")
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ response: "ok" }))
      await t.query({ query: "test" })
      const headers = mockFetch.mock.calls[0][1].headers
      expect(headers["Authorization"]).toBe("Bearer tok")
      expect(headers["X-API-Key"]).toBeUndefined()
    })

    it("sends no auth headers when neither token nor apiKey set", async () => {
      mockFetch.mockResolvedValueOnce(mockJsonResponse({ response: "ok" }))
      await tool.query({ query: "test" })
      const headers = mockFetch.mock.calls[0][1].headers
      expect(headers["Authorization"]).toBeUndefined()
      expect(headers["X-API-Key"]).toBeUndefined()
    })
  })
})
