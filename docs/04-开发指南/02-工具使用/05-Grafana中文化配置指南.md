# Grafana中文化配置指南

**状态**: ✅ 已完成  
**版本**: v1.0.0  
**创建日期**: 2025-12-22  
**最后更新**: 2025-12-22

---

## 📋 概述

本文档介绍如何将Grafana监控面板界面切换为中文，提升中文用户的使用体验。

---

## 🌏 支持的语言

Grafana官方支持多种语言，包括：
- 🇨🇳 简体中文 (zh-Hans)
- 🇹🇼 繁体中文 (zh-Hant)
- 🇺🇸 英语 (en)
- 🇯🇵 日语 (ja)
- 🇰🇷 韩语 (ko)
- 等其他语言

---

## ⚙️ 配置方法

### 方法一：环境变量配置（推荐）

已在 `docker-compose.yml` 中配置：

```yaml
grafana:
  environment:
    # 语言配置 - 中文界面
    GF_DEFAULT_LANGUAGE: zh-Hans
```

**优势**：
- ✅ 所有用户默认使用中文
- ✅ 新用户自动使用中文界面
- ✅ 配置简单，重启生效

---

### 方法二：用户个人设置

如果只想为特定用户设置中文：

1. 登录Grafana (http://localhost:3001)
2. 点击左下角头像
3. 选择 "Preferences" (偏好设置)
4. 在 "Language" 下拉菜单中选择 "中文（简体）"
5. 点击 "Save" 保存

**优势**：
- ✅ 每个用户可以选择自己喜欢的语言
- ✅ 不影响其他用户
- ✅ 无需重启服务

---

## 🚀 应用配置

### 方法1：完全重建容器（推荐）

```bash
# 停止并删除Grafana容器
docker-compose stop grafana
docker-compose rm -f grafana

# 重新创建并启动
docker-compose up -d grafana

# 等待30秒让Grafana完全启动
timeout /t 30
```

### 方法2：清除数据重新开始（如果方法1无效）

⚠️ **注意：此方法会清除所有Grafana配置和数据**

```bash
# 停止服务
docker-compose stop grafana

# 删除容器和数据卷
docker-compose rm -f grafana
docker volume rm build_body_grafana_data

# 重新启动
docker-compose up -d grafana
```

### 2. 验证配置

1. 访问 http://localhost:3001
2. 登录后界面应显示为中文
3. 检查以下元素是否已中文化：
   - ✅ 菜单栏
   - ✅ 按钮文字
   - ✅ 提示信息
   - ✅ 时间选择器

---

## 📊 面板标题中文化

### 当前状态

三个监控面板的标题已部分中文化：

1. **流式输出性能监控** ✅
   - 面板标题：中文
   - 指标名称：中文

2. **DAML-RAG Performance Dashboard** ⚠️
   - 面板标题：英文
   - 指标名称：英文

3. **Workflow Performance Optimization Dashboard** ⚠️
   - 面板标题：英文
   - 部分指标：中文

### 完全中文化建议

如需将所有面板标题改为中文，可以：

1. 在Grafana界面中编辑面板
2. 修改面板标题为中文
3. 保存面板配置

**建议的中文标题**：
- `DAML-RAG Performance Dashboard` → `DAML-RAG 性能监控`
- `Workflow Performance Optimization Dashboard` → `工作流性能优化监控`
- `Request Duration (P95)` → `请求耗时 (P95)`
- `Cache Hit Rate` → `缓存命中率`
- `Error Rate` → `错误率`

---

## 🎨 界面元素中文化对照

| 英文 | 中文 |
|------|------|
| Dashboard | 仪表板 |
| Query | 查询 |
| Alerts | 告警 |
| Status | 状态 |
| Time range | 时间范围 |
| Refresh | 刷新 |
| Last 6 hours | 最近6小时 |
| Table | 表格 |
| Graph | 图表 |
| Panel | 面板 |
| Edit | 编辑 |
| Share | 分享 |
| Export | 导出 |
| Settings | 设置 |

---

## 🔍 常见问题

### Q1: 为什么重启后还是英文？

**A**: 可能的原因：
1. 浏览器缓存：清除浏览器缓存后重试
2. 配置未生效：检查 `docker-compose.yml` 中的配置
3. 用户个人设置覆盖：检查用户偏好设置

**解决方法**：
```bash
# 1. 停止服务
docker-compose stop grafana

# 2. 删除容器（保留数据）
docker-compose rm -f grafana

# 3. 重新启动
docker-compose up -d grafana
```

---

### Q2: 部分文字还是英文？

**A**: 这是正常的，因为：
1. **系统界面**：已完全中文化 ✅
2. **面板标题**：需要手动修改 ⚠️
3. **指标名称**：由Prometheus定义，通常保持英文 ℹ️

**建议**：
- 系统界面使用中文
- 技术术语保持英文（如 TTFB、P95、P99）
- 面板标题使用中文

---

### Q3: 如何切换回英文？

**A**: 两种方法：

**方法1：修改环境变量**
```yaml
# docker-compose.yml
GF_DEFAULT_LANGUAGE: en  # 改为 en
```

**方法2：用户设置**
1. 点击头像 → Preferences
2. Language 选择 "English"
3. 保存

---

## 📝 配置文件位置

```
项目根目录/
├── docker-compose.yml              # Grafana语言配置
├── daml-rag-server/
│   └── config/
│       └── grafana/
│           ├── datasources/        # 数据源配置
│           └── dashboards/         # 面板配置
└── grafana_data/                   # Grafana数据（Docker卷）
```

---

## 🎯 最佳实践

1. **默认语言**
   - 团队主要语言设为默认语言
   - 允许用户个人自定义

2. **面板标题**
   - 技术术语保持英文（便于搜索和交流）
   - 描述性文字使用中文

3. **指标命名**
   - Prometheus指标名保持英文（标准规范）
   - 面板显示名称可以中文化

4. **文档**
   - 配置文档使用中文
   - 技术文档中英文结合

---

## 🔗 相关资源

- [Grafana官方文档 - 国际化](https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/#default_language)
- [Grafana支持的语言列表](https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/#supported-languages)
- [监控系统架构文档](../02-核心架构/05-监控层/01-监控系统架构.md)

---

**维护者**: 薛小川  
**最后更新**: 2025-12-22  
**版本**: v1.0.0
