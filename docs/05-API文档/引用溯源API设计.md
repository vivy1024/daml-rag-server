# 引用溯源API设计

**版本**: v1.0.0
**更新日期**: 2026-02-17
**状态**: ✅ 设计完成

## 概述

引用溯源API提供答案到具体文档+章节+位置的追溯能力，支持前端展示引用来源和用户验证信息准确性。

## 核心功能

1. **引用信息查询** - 获取特定查询的引用来源
2. **引用详情展示** - 展示引用的文档、章节、位置信息
3. **引用验证** - 验证LLM回答中的引用标记是否有效

## API端点设计

### 1. 获取引用信息

**端点**: `GET /api/ai/citations`

**描述**: 获取特定查询的引用来源信息

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query_id | string | 是 | 查询ID（从对话接口返回） |
| format | string | 否 | 返回格式：`detailed`（默认）或 `summary` |

**请求示例**:
```http
GET /api/ai/citations?query_id=abc123&format=detailed
Authorization: Bearer {token}
```

**响应格式**:
```json
{
    "code": 200,
    "msg": "获取引用信息成功",
    "data": {
        "query_id": "abc123",
        "query_text": "深蹲的正确姿势",
        "citations": [
            {
                "citation_id": 1,
                "source_file": "bilibili_subtitle",
                "source_type": "video",
                "doc_title": "NSCA力量训练基础课程",
                "section_path": "深蹲技术要点",
                "content_type": "exercise",
                "relevance_score": 0.8945,
                "text_preview": "深蹲时保持脊柱中立，膝盖与脚尖方向一致...",
                "chunk_index": 12,
                "total_chunks": 45,
                "position_label": "中间",
                "position_ratio": 0.267,
                "bvid": "BV1xx411c7XD",
                "timestamp_start": 360,
                "timestamp_end": 390,
                "video_title": "NSCA力量训练基础课程"
            },
            {
                "citation_id": 2,
                "source_file": "books/NSCA_Foundations.pdf",
                "source_type": "pdf",
                "doc_title": "NSCA Foundations of Fitness Programming",
                "section_path": "Chapter 3 > Resistance Training",
                "content_type": "exercise",
                "relevance_score": 0.8723,
                "text_preview": "渐进超负荷原则是力量训练的基础...",
                "chunk_index": 28,
                "total_chunks": 120,
                "position_label": "前部",
                "position_ratio": 0.233
            }
        ],
        "grouped_citations": {
            "NSCA力量训练基础课程": [
                {
                    "citation_id": 1,
                    "section_path": "深蹲技术要点",
                    "position_label": "中间"
                }
            ],
            "NSCA Foundations of Fitness Programming": [
                {
                    "citation_id": 2,
                    "section_path": "Chapter 3 > Resistance Training",
                    "position_label": "前部"
                }
            ]
        },
        "total_sources": 2,
        "total_citations": 2,
        "source_types": {
            "video": 1,
            "pdf": 1
        },
        "content_types": {
            "exercise": 2
        },
        "avg_relevance": 0.8834
    }
}
```

**错误响应**:
```json
{
    "code": 404,
    "msg": "未找到该查询的引用信息",
    "data": null
}
```

### 2. 获取引用详情

**端点**: `GET /api/ai/citations/{citation_id}`

**描述**: 获取单个引用的详细信息

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| citation_id | integer | 是 | 引用ID（路径参数） |
| query_id | string | 是 | 查询ID（查询参数） |

**请求示例**:
```http
GET /api/ai/citations/1?query_id=abc123
Authorization: Bearer {token}
```

**响应格式**:
```json
{
    "code": 200,
    "msg": "获取引用详情成功",
    "data": {
        "citation_id": 1,
        "source_file": "bilibili_subtitle",
        "source_type": "video",
        "doc_title": "NSCA力量训练基础课程",
        "section_path": "深蹲技术要点",
        "content_type": "exercise",
        "relevance_score": 0.8945,
        "full_text": "深蹲时保持脊柱中立，膝盖与脚尖方向一致，下蹲至大腿与地面平行或略低...",
        "chunk_index": 12,
        "total_chunks": 45,
        "position_label": "中间",
        "position_ratio": 0.267,
        "bvid": "BV1xx411c7XD",
        "timestamp_start": 360,
        "timestamp_end": 390,
        "video_url": "https://www.bilibili.com/video/BV1xx411c7XD?t=360",
        "keywords": ["深蹲", "姿势", "技术要点"],
        "language": "zh",
        "char_count": 256
    }
}
```

### 3. 验证引用标记

**端点**: `POST /api/ai/citations/validate`

**描述**: 验证LLM回答中的引用标记是否有效

**请求体**:
```json
{
    "query_id": "abc123",
    "answer_text": "深蹲时要注意[1]保持脊柱中立，[2]膝盖与脚尖方向一致。"
}
```

**响应格式**:
```json
{
    "code": 200,
    "msg": "引用验证完成",
    "data": {
        "is_valid": true,
        "total_citations": 2,
        "used_citations": 2,
        "invalid_citations": [],
        "citation_details": [
            {
                "citation_id": 1,
                "is_used": true,
                "doc_title": "NSCA力量训练基础课程"
            },
            {
                "citation_id": 2,
                "is_used": true,
                "doc_title": "NSCA Foundations of Fitness Programming"
            }
        ]
    }
}
```

## 前端展示建议

### 1. 引用标记展示

在LLM回答中，将 `[1]` `[2]` 等标记渲染为可点击的链接：

```html
<span class="citation-mark" @click="showCitationDetail(1)">
  [1]
</span>
```

### 2. 引用列表展示

在回答下方展示引用来源列表：

```html
<div class="citations-list">
  <h4>参考资料</h4>
  <div v-for="citation in citations" :key="citation.citation_id">
    <div class="citation-item">
      <span class="citation-id">[{{ citation.citation_id }}]</span>
      <span class="source-type-icon">{{ getSourceIcon(citation.source_type) }}</span>
      <span class="doc-title">{{ citation.doc_title }}</span>
      <span class="section">{{ citation.section_path }}</span>
      <span class="position">（{{ citation.position_label }}）</span>
      <span class="relevance">相关度: {{ (citation.relevance_score * 100).toFixed(1) }}%</span>
    </div>
  </div>
</div>
```

### 3. 引用详情弹窗

点击引用标记时，弹出详情窗口：

```html
<div class="citation-modal">
  <h3>{{ citation.doc_title }}</h3>
  <p class="section-path">{{ citation.section_path }}</p>
  <div class="citation-content">
    {{ citation.full_text }}
  </div>
  <div class="citation-meta">
    <span>来源类型: {{ citation.source_type }}</span>
    <span>位置: {{ citation.position_label }}</span>
    <span>相关度: {{ (citation.relevance_score * 100).toFixed(1) }}%</span>
  </div>
  <!-- 对于视频来源，显示跳转链接 -->
  <a v-if="citation.video_url" :href="citation.video_url" target="_blank">
    观看视频片段 ({{ formatTimestamp(citation.timestamp_start) }})
  </a>
</div>
```

## 数据流程

```
用户查询
  ↓
DAML-RAG检索（三层检索）
  ↓
生成引用信息（CitationTracker）
  ↓
存储到Redis（key: citations:{query_id}）
  ↓
返回query_id给前端
  ↓
前端调用 /api/ai/citations?query_id=xxx
  ↓
展示引用来源
```

## 缓存策略

- **Redis缓存**: 引用信息缓存24小时
- **缓存键格式**: `citations:{query_id}`
- **缓存内容**: 完整的引用信息JSON

## 性能优化

1. **批量查询**: 支持一次查询多个citation_id
2. **分页**: 引用列表支持分页（默认20条/页）
3. **懒加载**: 引用详情按需加载
4. **预加载**: 前3个引用详情预加载

## 安全考虑

1. **权限验证**: 需要有效的JWT token
2. **查询限制**: 每个用户每分钟最多查询60次
3. **数据脱敏**: 不返回敏感的内部路径信息

## 错误码

| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 参数错误 |
| 401 | 未授权 |
| 404 | 未找到引用信息 |
| 429 | 请求频率超限 |
| 500 | 服务器错误 |

## 未来扩展

1. **引用评分**: 用户可以对引用的有用性进行评分
2. **引用导出**: 支持导出引用列表为PDF/Markdown
3. **引用分享**: 生成引用分享链接
4. **引用历史**: 查看用户的引用查询历史

---

**维护者**: 薛小川
**最后更新**: 2026-02-17
