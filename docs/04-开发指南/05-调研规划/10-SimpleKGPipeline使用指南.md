# SimpleKGPipeline 教材知识提取使用指南

**版本**: v2.0.0
**日期**: 2026-02-16
**状态**: ✅ 已完成

---

## 📋 概述

本指南介绍如何使用 `extract_textbook_knowledge.py` 脚本从健身教材中提取知识图谱，并存储到 Neo4j 数据库中。

---

## 🎯 功能特性

- ✅ 支持 PDF 和文本输入
- ✅ 支持批量提取多个 PDF 文件
- ✅ 断点续传（记录已处理的文件）
- ✅ Dry-run 模式（不写入数据库，仅输出提取结果）
- ✅ 详细的提取统计和日志
- ✅ 使用 DeepSeek API 进行实体和关系提取
- ✅ 使用 GTE-Large-zh 生成嵌入向量
- ✅ 支持 Docker volume mount（教材自动挂载到容器）

---

## 📦 依赖安装

在 Docker 容器内安装必要的依赖：

```bash
docker exec fitness_daml_rag bash -c "pip install 'neo4j-graphrag[openai]'"
```

---

## 📁 文件结构

```
build_body/
├── .books/                            # 教材 PDF 文件（宿主机）
│   ├── Open-Textbook-of-Exercise-Physiology-1756071395.pdf
│   ├── foundationsoffitnessprogramming_201508.pdf
│   ├── Introduction_to_Sports_Biomechanics.pdf
│   └── AMJ-04-107.pdf
├── daml-rag-server/
│   ├── config/
│   │   ├── kg_extraction_schema.yaml      # Schema 配置（节点和关系类型）
│   │   └── kg_pipeline_config.yaml        # Pipeline 配置（LLM、Embedder 等）
│   ├── scripts/
│   │   ├── extract_textbook_knowledge.py  # 提取脚本
│   │   ├── test_extract_single_v2.bat     # 测试脚本（Windows）
│   │   └── batch_extract_textbooks_v2.bat # 批量提取脚本（Windows）
│   ├── data/
│   │   ├── extraction_checkpoint.json     # 检查点文件（自动生成）
│   │   └── extraction_results/            # 提取结果目录（自动生成）
│   └── logs/
│       └── kg_extraction.log              # 日志文件（自动生成）
└── docker-compose.yml                     # 包含 volume mount: ./.books:/app/books:ro
```

**Volume Mount 配置**：
- 宿主机路径：`./.books/`
- 容器内路径：`/app/books/`
- 权限：只读（`:ro`）

---

## 🔧 配置说明

### 1. Schema 配置（kg_extraction_schema.yaml）

定义了从教材中提取的节点和关系类型：

**节点类型**（5种）：
- `Concept`: 运动科学概念（如"超补偿"、"渐进超负荷"）
- `Principle`: 训练原则（如"FITT原则"、"特异性原则"）
- `Mechanism`: 生理机制（如"肌肉肥大机制"、"能量系统"）
- `Guideline`: 训练指南（如"ACSM力量训练指南"）
- `ResearchFinding`: 研究发现（如"最佳训练频率研究"）

**关系类型**（6种）：
- `EXPLAINS`: 概念解释机制
- `BASED_ON`: 原则基于概念
- `RECOMMENDS`: 指南推荐动作/原则
- `SUPPORTS`: 研究支持概念/原则
- `APPLIES_TO`: 原则应用于动作/肌肉
- `CONTRADICTS`: 研究之间的矛盾

**溯源字段**：
- `source_textbook`: 来源教材
- `chapter`: 章节
- `page_range`: 页码范围

### 2. Pipeline 配置（kg_pipeline_config.yaml）

配置了提取流程的各个组件：

- **LLM**: DeepSeek API（支持 10 个 API Key 轮换）
- **Embedder**: GTE-Large-zh（1024维）
- **Neo4j**: 连接配置
- **Text Splitter**: chunk_size=1000, overlap=200
- **断点续传**: 每处理 10 页保存一次检查点
- **日志**: INFO 级别，保存到 logs/kg_extraction.log

---

## 🚀 使用方法

### 方法 1: 使用批量提取脚本（推荐）

#### 1.1 重启容器（使 volume mount 生效）

```bash
docker-compose restart fitness_daml_rag
```

#### 1.2 测试单个教材提取

**Windows**:
```bash
cd F:\build_body\daml-rag-server\scripts
test_extract_single_v2.bat
```

**Linux/Mac**:
```bash
cd /path/to/build_body/daml-rag-server/scripts
bash test_extract_single_v2.sh
```

#### 1.3 批量提取所有教材

**Windows**:
```bash
cd F:\build_body\daml-rag-server\scripts
batch_extract_textbooks_v2.bat
```

**Linux/Mac**:
```bash
cd /path/to/build_body/daml-rag-server/scripts
bash batch_extract_textbooks_v2.sh
```

### 方法 2: 手动运行提取脚本

#### 2.1 单个 PDF 提取

```bash
docker exec fitness_daml_rag bash -c "cd /app && python scripts/extract_textbook_knowledge.py \
  --mode pdf \
  --input /app/books/AMJ-04-107.pdf"
```

#### 2.2 批量 PDF 提取

```bash
docker exec fitness_daml_rag bash -c "cd /app && python scripts/extract_textbook_knowledge.py \
  --mode batch \
  --input /app/books \
  --pattern '*.pdf'"
```

#### 2.3 文本文件提取

```bash
docker exec fitness_daml_rag bash -c "cd /app && python scripts/extract_textbook_knowledge.py \
  --mode text \
  --input /app/data/test_textbook.txt"
```

#### 2.4 Dry-run 模式（测试）

```bash
docker exec fitness_daml_rag bash -c "cd /app && python scripts/extract_textbook_knowledge.py \
  --mode text \
  --input /app/data/test_textbook.txt \
  --dry-run"
```

---

## 📊 输出示例

### 成功提取

```json
{
  "file_path": "/path/to/textbook.pdf",
  "status": "success",
  "nodes_created": 45,
  "relationships_created": 67,
  "timestamp": "2026-02-16T15:14:46.550180"
}
```

### 批量提取统计

```
============================================================
批量提取完成
  - 总文件数: 4
  - 成功: 4
  - 失败: 0
  - 总节点数: 180
  - 总关系数: 268
============================================================
```

---

## 🔍 验证提取结果

### 1. 查看节点数量

```cypher
// 查看新增的节点类型
MATCH (n)
WHERE n:Concept OR n:Principle OR n:Mechanism OR n:Guideline OR n:ResearchFinding
RETURN labels(n)[0] as NodeType, count(*) as Count
ORDER BY Count DESC
```

### 2. 查看关系数量

```cypher
// 查看新增的关系类型
MATCH ()-[r]->()
WHERE type(r) IN ['EXPLAINS', 'BASED_ON', 'RECOMMENDS', 'SUPPORTS', 'APPLIES_TO', 'CONTRADICTS']
RETURN type(r) as RelationType, count(*) as Count
ORDER BY Count DESC
```

### 3. 查看特定概念

```cypher
// 查看"渐进超负荷"概念及其关系
MATCH (c:Concept {name: '渐进超负荷'})
OPTIONAL MATCH (c)-[r]->(related)
RETURN c, r, related
```

---

## ⚠️ 注意事项

### 1. Neo4j APOC 插件

当前 Neo4j 实例缺少 APOC 插件中的 `db.create.setRelationshipVectorProperty` 存储过程。这会导致关系向量属性无法存储，但不影响节点和关系的提取。

**解决方案**：
- 安装 APOC 插件：https://neo4j.com/labs/apoc/
- 或者修改 neo4j-graphrag 配置，禁用关系向量属性

### 2. API 限流

DeepSeek API 有速率限制。如果遇到限流错误，脚本会自动轮换到下一个 API Key。

### 3. 断点续传

如果提取过程中断，再次运行脚本时会自动跳过已处理的文件。检查点文件位于 `data/extraction_checkpoint.json`。

### 4. 内存使用

大型 PDF 文件可能占用较多内存。建议：
- 单个 PDF 文件不超过 100MB
- 批量提取时，每次处理不超过 10 个文件

---

## 🐛 故障排查

### 问题 1: 找不到配置文件

**错误信息**：
```
FileNotFoundError: 配置文件不存在: /app/config/kg_pipeline_config.yaml
```

**解决方案**：
确保配置文件存在，或使用 `--config` 参数指定配置文件路径。

### 问题 2: Neo4j 连接失败

**错误信息**：
```
❌ Neo4j 连接失败: Unable to retrieve routing information
```

**解决方案**：
- 检查 Neo4j 服务是否运行：`docker ps | grep neo4j`
- 检查环境变量：`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`

### 问题 3: LLM API 调用失败

**错误信息**：
```
ImportError: Could not import openai Python client
```

**解决方案**：
```bash
docker exec fitness_daml_rag bash -c "pip install 'neo4j-graphrag[openai]'"
```

### 问题 4: 嵌入模型加载失败

**错误信息**：
```
OSError: Can't load tokenizer for 'thenlper/gte-large-zh'
```

**解决方案**：
- 检查网络连接（需要从 HuggingFace 下载模型）
- 或者预先下载模型到 `/root/.cache/huggingface/hub`

---

## 📚 参考资料

- **neo4j-graphrag-python 文档**: https://neo4j.com/docs/neo4j-graphrag-python/current/
- **SimpleKGPipeline API**: https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html#kg-builder
- **DeepSeek API**: https://platform.deepseek.com/docs
- **GTE-Large-zh 模型**: https://huggingface.co/thenlper/gte-large-zh

---

## 🔄 后续优化

1. **安装 APOC 插件**：解决关系向量属性存储问题
2. **优化 Schema**：根据实际提取结果调整节点和关系类型
3. **添加质量检查**：验证提取的实体和关系的准确性
4. **支持增量更新**：只提取新增或修改的内容
5. **添加可视化**：使用 Neo4j Browser 或 Bloom 可视化知识图谱

---

**维护者**: 薛小川
**最后更新**: 2026-02-16
