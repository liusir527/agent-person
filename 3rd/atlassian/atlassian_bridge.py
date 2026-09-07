#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP Atlassian Bridge - 轻量桥接服务
仅暴露 9 个最常用的 JIRA / Confluence 工具，压缩上下文 token 占用。
"""

import json
import sys
import os
import io
from pathlib import Path

# ── 强制 stdout/stdin 为 UTF-8 ──
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stdin.reconfigure(encoding='utf-8')
elif hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')


# ═══════════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════════

def _ensure_jira_env():
    """检查 JIRA 环境变量，返回 (url, token) 或抛出异常"""
    url = os.environ.get("JIRA_URL", "").strip()
    token = os.environ.get("JIRA_PERSONAL_TOKEN", "").strip()
    if not url:
        raise ValueError("缺少环境变量 JIRA_URL")
    if not token:
        raise ValueError("缺少环境变量 JIRA_PERSONAL_TOKEN")
    return url, token


def _ensure_confluence_env():
    """检查 Confluence 环境变量，返回 (url, token) 或抛出异常"""
    url = os.environ.get("CONFLUENCE_URL", "").strip()
    token = os.environ.get("CONFLUENCE_PERSONAL_TOKEN", "").strip()
    if not url:
        raise ValueError("缺少环境变量 CONFLUENCE_URL")
    if not token:
        raise ValueError("缺少环境变量 CONFLUENCE_PERSONAL_TOKEN")
    return url, token


def _get_jira():
    """延迟导入并创建 Jira 客户端"""
    from atlassian import Jira
    url, token = _ensure_jira_env()
    return Jira(url=url, token=token, cloud=False)


def _get_confluence():
    """延迟导入并创建 Confluence 客户端"""
    from atlassian import Confluence
    url, token = _ensure_confluence_env()
    return Confluence(url=url, token=token, cloud=False)


# ── JIRA 工具 ──

def jira_search(jql: str, max_results: int = 50, fields: str = "") -> str:
    """JQL 搜索工单

    :param jql: JQL 查询语句，如 'project = PROJ AND status = Open'
    :param max_results: 最大返回条数，默认 50
    :param fields: 逗号分隔的字段列表，如 'summary,status,assignee,priority'；为空则返回默认字段
    """
    try:
        jira = _get_jira()
        field_list = [f.strip() for f in fields.split(",") if f.strip()] if fields else None
        result = jira.jql(jql, limit=max_results, fields=field_list)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def jira_get_issue(issue_key: str) -> str:
    """获取单个工单详情

    :param issue_key: 工单 key，如 'PROJ-123'
    """
    try:
        jira = _get_jira()
        result = jira.get_issue(issue_key, expand="changelog,comments,transitions")
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def jira_create_issue(project_key: str, issue_type: str, summary: str,
                      description: str = "", priority: str = "",
                      assignee: str = "", labels: str = "") -> str:
    """创建工单

    :param project_key: 项目 key，如 'PROJ'
    :param issue_type: 问题类型，如 'Bug', 'Task', 'Story'
    :param summary: 工单标题
    :param description: 工单描述（可选）
    :param priority: 优先级（可选），如 'High', 'Highest'
    :param assignee: 经办人用户名（可选）
    :param labels: 逗号分隔的标签列表（可选），如 'backend,urgent'
    """
    try:
        jira = _get_jira()
        fields = {
            "project": {"key": project_key},
            "issuetype": {"name": issue_type},
            "summary": summary,
        }
        if description:
            fields["description"] = description
        if priority:
            fields["priority"] = {"name": priority}
        if assignee:
            fields["assignee"] = {"name": assignee}
        if labels:
            fields["labels"] = [l.strip() for l in labels.split(",") if l.strip()]

        result = jira.create_issue(fields=fields)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def jira_update_issue(issue_key: str, summary: str = "", priority: str = "",
                      assignee: str = "", labels: str = "",
                      description: str = "") -> str:
    """更新工单字段

    :param issue_key: 工单 key，如 'PROJ-123'
    :param summary: 新标题（留空不修改）
    :param priority: 新优先级（留空不修改），如 'High'
    :param assignee: 新经办人（留空不修改）
    :param labels: 新标签列表（留空不修改），逗号分隔
    :param description: 新描述（留空不修改）
    """
    try:
        jira = _get_jira()
        fields = {}
        if summary:
            fields["summary"] = summary
        if priority:
            fields["priority"] = {"name": priority}
        if assignee:
            fields["assignee"] = {"name": assignee}
        if labels:
            fields["labels"] = [l.strip() for l in labels.split(",") if l.strip()]
        if description:
            fields["description"] = description

        if not fields:
            return json.dumps({"error": "没有提供要更新的字段"}, ensure_ascii=False)

        result = jira.update_issue_field(issue_key, fields=fields)
        return json.dumps({"success": True, "issue_key": issue_key}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def jira_add_comment(issue_key: str, body: str) -> str:
    """添加工单评论

    :param issue_key: 工单 key，如 'PROJ-123'
    :param body: 评论内容
    """
    try:
        jira = _get_jira()
        result = jira.add_comment(issue_key, body)
        return json.dumps({"success": True, "issue_key": issue_key}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ── Confluence 工具 ──

def confluence_search(cql: str, limit: int = 25) -> str:
    """CQL 搜索 Confluence 页面

    :param cql: CQL 查询语句，如 'space = "DEV" AND type = page'
    :param limit: 最大返回条数，默认 25
    """
    try:
        confluence = _get_confluence()
        result = confluence.cql(cql, limit=limit, expand="body.storage,version,ancestors")
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def confluence_get_page(page_id: str) -> str:
    """获取页面内容

    :param page_id: 页面 ID
    """
    try:
        confluence = _get_confluence()
        result = confluence.get_page_by_id(
            page_id, expand="body.storage,version,ancestors,children.page"
        )
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def confluence_create_page(space_key: str, title: str, body: str,
                           parent_id: str = "") -> str:
    """创建页面

    :param space_key: 空间 key，如 'DEV'
    :param title: 页面标题
    :param body: 页面内容（HTML 格式）
    :param parent_id: 父页面 ID（可选）
    """
    try:
        confluence = _get_confluence()
        result = confluence.create_page(
            space=space_key,
            title=title,
            body=body,
            parent_id=parent_id if parent_id else None,
        )
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def confluence_update_page(page_id: str, title: str, body: str) -> str:
    """更新页面内容

    :param page_id: 页面 ID
    :param title: 页面标题
    :param body: 页面内容（HTML 格式）
    """
    try:
        confluence = _get_confluence()
        # 先获取当前版本号
        current = confluence.get_page_by_id(page_id, expand="version")
        version = current.get("version", {}).get("number", 0) + 1
        result = confluence.update_page(
            page_id=page_id,
            title=title,
            body=body,
            version=version,
        )
        return json.dumps({"success": True, "page_id": page_id}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════════
# MCP 服务器实现（JSON-RPC over stdio）
# ═══════════════════════════════════════════════════════════════════

TOOL_DEFINITIONS = [
    {
        "name": "jira_search",
        "description": "JQL 搜索 JIRA 工单。先用 maxResults=1 测试再完整执行。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "jql": {"type": "string", "description": "JQL 查询语句，如 'project = PROJ AND status = Open'"},
                "max_results": {"type": "integer", "description": "最大返回条数，默认 50", "default": 50},
                "fields": {"type": "string", "description": "逗号分隔的字段列表，如 'summary,status,assignee'；留空返回默认字段", "default": ""},
            },
            "required": ["jql"],
        },
    },
    {
        "name": "jira_get_issue",
        "description": "获取单个 JIRA 工单详情，包含变更日志、评论和流转。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "issue_key": {"type": "string", "description": "工单 key，如 'PROJ-123'"},
            },
            "required": ["issue_key"],
        },
    },
    {
        "name": "jira_create_issue",
        "description": "在 JIRA 项目中创建新工单。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_key": {"type": "string", "description": "项目 key，如 'PROJ'"},
                "issue_type": {"type": "string", "description": "问题类型，如 'Bug', 'Task', 'Story'"},
                "summary": {"type": "string", "description": "工单标题"},
                "description": {"type": "string", "description": "工单描述（可选）", "default": ""},
                "priority": {"type": "string", "description": "优先级（可选），如 'High', 'Highest'", "default": ""},
                "assignee": {"type": "string", "description": "经办人用户名（可选）", "default": ""},
                "labels": {"type": "string", "description": "逗号分隔的标签（可选），如 'backend,urgent'", "default": ""},
            },
            "required": ["project_key", "issue_type", "summary"],
        },
    },
    {
        "name": "jira_update_issue",
        "description": "更新现有 JIRA 工单的字段。只传需要修改的字段。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "issue_key": {"type": "string", "description": "工单 key，如 'PROJ-123'"},
                "summary": {"type": "string", "description": "新标题（留空不修改）", "default": ""},
                "priority": {"type": "string", "description": "新优先级（留空不修改）", "default": ""},
                "assignee": {"type": "string", "description": "新经办人（留空不修改）", "default": ""},
                "labels": {"type": "string", "description": "新标签（留空不修改），逗号分隔", "default": ""},
                "description": {"type": "string", "description": "新描述（留空不修改）", "default": ""},
            },
            "required": ["issue_key"],
        },
    },
    {
        "name": "jira_add_comment",
        "description": "向 JIRA 工单添加评论。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "issue_key": {"type": "string", "description": "工单 key，如 'PROJ-123'"},
                "body": {"type": "string", "description": "评论内容"},
            },
            "required": ["issue_key", "body"],
        },
    },
    {
        "name": "confluence_search",
        "description": "CQL 搜索 Confluence 页面。先用 limit=1 测试再完整执行。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cql": {"type": "string", "description": "CQL 查询语句，如 'space = \"DEV\" AND type = page'"},
                "limit": {"type": "integer", "description": "最大返回条数，默认 25", "default": 25},
            },
            "required": ["cql"],
        },
    },
    {
        "name": "confluence_get_page",
        "description": "获取 Confluence 页面内容，包含正文、版本、父级和子页面。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "页面 ID"},
            },
            "required": ["page_id"],
        },
    },
    {
        "name": "confluence_create_page",
        "description": "在 Confluence 空间中创建新页面。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "space_key": {"type": "string", "description": "空间 key，如 'DEV'"},
                "title": {"type": "string", "description": "页面标题"},
                "body": {"type": "string", "description": "页面内容（HTML 格式）"},
                "parent_id": {"type": "string", "description": "父页面 ID（可选）", "default": ""},
            },
            "required": ["space_key", "title", "body"],
        },
    },
    {
        "name": "confluence_update_page",
        "description": "更新 Confluence 页面内容。自动处理版本号递增。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "页面 ID"},
                "title": {"type": "string", "description": "页面标题"},
                "body": {"type": "string", "description": "页面内容（HTML 格式）"},
            },
            "required": ["page_id", "title", "body"],
        },
    },
]

HANDLERS = {
    "jira_search": jira_search,
    "jira_get_issue": jira_get_issue,
    "jira_create_issue": jira_create_issue,
    "jira_update_issue": jira_update_issue,
    "jira_add_comment": jira_add_comment,
    "confluence_search": confluence_search,
    "confluence_get_page": confluence_get_page,
    "confluence_create_page": confluence_create_page,
    "confluence_update_page": confluence_update_page,
}


class AtlassianBridgeServer:
    """MCP over stdio server"""

    def __init__(self):
        self.tools = {t["name"]: t for t in TOOL_DEFINITIONS}

    def _send(self, response):
        """向 stdout 写入 JSON-RPC 响应"""
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + '\n')
        sys.stdout.flush()

    def _handle_initialize(self, req_id, params):
        protocol_version = params.get("protocolVersion", "2024-11-05")
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": protocol_version,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "atlassian-bridge", "version": "1.0.0"},
            },
        }

    def _handle_list(self, req_id):
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": t["name"],
                        "description": t["description"],
                        "inputSchema": t["inputSchema"],
                    }
                    for t in self.tools.values()
                ]
            },
        }

    def _handle_call(self, req_id, name, arguments):
        if name not in HANDLERS:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Tool not found: {name}"},
            }
        try:
            result = HANDLERS[name](**arguments)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": result}]},
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": str(e)},
            }

    def handle_request(self, request):
        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if method == "initialize":
            return self._handle_initialize(req_id, params)
        elif method == "notifications/initialized":
            return None
        elif method == "tools/list":
            return self._handle_list(req_id)
        elif method == "tools/call":
            return self._handle_call(req_id, params.get("name", ""), params.get("arguments", {}))
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }

    def run(self):
        """stdio 主循环（兼容 nf_simple 的行协议）"""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                continue

            response = self.handle_request(request)
            if response is not None:
                self._send(response)


def main():
    server = AtlassianBridgeServer()
    server.run()


if __name__ == "__main__":
    main()