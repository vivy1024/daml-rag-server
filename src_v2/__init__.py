"""
DAML-RAG v2 — 浪潮检索引擎 + MCP 工具层

架构:
  src_v2/
  ├── config.py          # 统一配置
  ├── server.py          # MCP 协议服务器
  ├── data/              # 数据层（内存加载）
  ├── engine/            # 浪潮引擎（检索管线）
  ├── rules/             # 安全规则引擎
  └── tools/             # MCP 工具实现
"""

__version__ = "2.0.0"
