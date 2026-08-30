"""Page (frontend route) definitions and permission keys.

Used by both backend access control and the permissions-management UI.
"""
from __future__ import annotations

# All pages in the sidebar. ``label`` is the Chinese display name.
PAGE_DEFINITIONS: list[dict[str, str | bool]] = [
    {"key": "dashboard", "label": "概览", "grantable": True},
    {"key": "officials", "label": "履历档案", "grantable": True},
    {"key": "timeline", "label": "时间线", "grantable": True},
    {"key": "relations", "label": "关系图谱", "grantable": True},
    {"key": "info_sources", "label": "信息源管理", "grantable": True},
    {"key": "analysis", "label": "智能分析", "grantable": True},
    {"key": "task_center", "label": "任务中心", "grantable": True},
    {"key": "system_config", "label": "系统配置", "grantable": True},
    {"key": "permission", "label": "权限管理", "grantable": False},  # admin only
]

# 页面合并/改名后的权限键别名：启动迁移时把旧键改写为新键。
PAGE_KEY_ALIASES: dict[str, str] = {
    "analysis_tasks": "analysis",
    "analysis_result": "analysis",
}

ALL_PAGE_KEYS: list[str] = [p["key"] for p in PAGE_DEFINITIONS]  # type: ignore[misc]
ADMIN_ONLY_PAGE_KEYS: set[str] = {
    p["key"] for p in PAGE_DEFINITIONS if not p["grantable"]  # type: ignore[misc]
}
GRANTABLE_PAGE_KEYS: list[str] = [
    p["key"] for p in PAGE_DEFINITIONS if p["grantable"]  # type: ignore[misc]
]


def page_label(key: str) -> str:
    for p in PAGE_DEFINITIONS:
        if p["key"] == key:
            return str(p["label"])
    return key
