# 用户档案MCP数据结构

**版本**: v2.3.0  
**创建日期**: 2025-12-19  
**更新日期**: 2025-12-20  
**状态**: ✅ 生产就绪

---

## 概述

用户档案MCP服务（user-profile-stdio）是DAML-RAG系统的核心数据服务，负责管理用户的健身档案、营养配置、训练目标等信息。该服务通过stdio协议与DAML-RAG服务通信，提供用户数据的CRUD操作。

**服务特点**：
- **数据源**：PHP后端MySQL数据库（主）+ 本地JSON文件（备份）
- **通信协议**：stdio（进程内通信）
- **数据格式**：JSON
- **会话管理**：支持临时会话存储（1小时TTL）
- **前端集成**：支持从前端localStorage同步数据

**混合方案架构（v3.2.0）**：
```
步骤1预加载（主路径）
  ↓ 失败
用户档案MCP工具（降级路径）
  ↓ 失败
匿名模式（最终降级）

DAG编排器访问：
  优先从context获取（0延迟）
  ↓ 没有
  调用MCP工具（stdio）
```

**性能对比**：
- 预加载首次：4.6秒，缓存命中：<100ms
- DAG任务访问：0ms（从context获取）
- MCP工具调用：8.2秒（降级路径）

---

## 核心数据结构

### UserProfile（用户档案）

用户档案是系统中最核心的数据结构，包含用户的所有健身相关信息。

```typescript
interface UserProfile {
  user_id: string;                    // 用户唯一标识
  basic_info: UserBasicInfo;          // 基础信息
  nutrition_profile: NutritionProfile; // 营养档案
  fitness_config: FitnessConfig;      // 健身配置
  fitness_goals: FitnessGoals;        // 健身目标
  strength_levels: StrengthLevels;    // 力量水平
  health_profile: HealthProfile;      // 健康档案
  created_at: string;                 // 创建时间（ISO 8601）
  updated_at: string;                 // 更新时间（ISO 8601）
}
```

---

## 子结构详解

### 1. UserBasicInfo（基础信息）

存储用户的基本身体数据和计算指标。

```typescript
interface UserBasicInfo {
  age?: number;                    // 年龄（岁）
  gender?: string;                 // 性别（男/女）
  height?: number;                 // 身高（cm）
  weight?: number;                 // 体重（kg）
  body_fat_percentage?: number;    // 体脂率（%）
  bmi?: number;                    // BMI指数（自动计算）
  ffmi?: number;                   // 无脂体重指数（自动计算）
}
```

**计算公式**：
```typescript
// BMI计算
bmi = weight / (height/100)²

// FFMI计算
lean_mass = weight × (1 - body_fat_percentage/100)
ffmi = lean_mass / (height/100)²
```

---

### 2. NutritionProfile（营养档案）

存储用户的营养相关配置和目标。

```typescript
interface NutritionProfile {
  // 地区和人群分类
  region?: string;                 // 地区（华北、东北、华东、华南、西南、西北、华中）
  population?: string;             // 人群类型
  age_gender_group?: string;       // 年龄性别组
  
  // 饮食偏好和限制
  dietary_preferences?: string[];  // 饮食偏好（低碳水、高蛋白、素食等）
  allergies?: string[];            // 过敏食物
  supplements?: string[];          // 补剂使用
  budget_level?: string;           // 预算限制（low/moderate/high）
  
  // 营养目标（AI自动计算）
  daily_calorie_target?: number;   // 每日热量目标（kcal）
  daily_protein_target?: number;   // 每日蛋白质目标（g）
  meal_frequency?: number;         // 每日餐数（3-6餐）
}
```

---

### 3. FitnessConfig（健身配置）

存储用户的训练相关配置。

```typescript
interface FitnessConfig {
  // 训练经验和水平
  training_experience_months?: number;  // 训练经验（月）
  fitness_level?: string;               // 健身水平（beginner/intermediate/advanced/elite）
  
  // 训练计划配置
  preferred_rest_pattern?: string;      // 休息模式（练一休一、练二休一等）
  preferred_training_split?: string;    // 训练分化（推拉腿、上下肢、全身、部位）
  training_days_per_week?: number;      // 每周训练天数（1-7天）
  training_duration_per_session?: number; // 每次训练时长（分钟）
  
  // 训练环境和偏好
  training_location?: string;           // 训练场地（健身房/家里/户外/混合）
  exercise_preferences?: string[];      // 运动偏好
  disliked_exercises?: string[];        // 不喜欢的动作
  sleep_hours?: number;                 // 每晚睡眠小时数
}
```

**休息模式智能推荐**：
- `beginner` → 练一休一
- `novice` → 练二休一
- `intermediate` → 练三休一
- `advanced` → 练四休一

---

### 4. FitnessGoals（健身目标）

```typescript
interface FitnessGoals {
  primary_goal?: string;        // 主要目标（增肌、减脂、力量、耐力、健康）
  target_weight?: number;       // 目标体重（kg）
  secondary_goals?: string[];   // 次要目标
}
```

---

### 5. StrengthLevels（力量水平）

```typescript
interface StrengthLevels {
  squat_1rm?: number;           // 深蹲1RM（kg）
  bench_press_1rm?: number;     // 卧推1RM（kg）
  deadlift_1rm?: number;        // 硬拉1RM（kg）
  [key: string]: number | undefined;  // 支持其他动作的1RM
}
```

---

### 6. HealthProfile（健康档案）

```typescript
interface HealthProfile {
  injury_history?: Array<{
    type: string;           // 损伤类型
    severity: string;       // 严重程度（mild/moderate/severe）
    date: string;           // 发生日期
    recovered: boolean;     // 是否已康复
    notes?: string;         // 备注
  }>;
  health_conditions?: string[];  // 健康状况（高血压、糖尿病等）
  medications?: string[];        // 用药情况
}
```

---

### 7. TrainingFeedback（训练反馈）

```typescript
interface TrainingFeedback {
  session_id: string;           // 训练会话ID
  date: string;                 // 日期
  fatigue_level: number;        // 疲劳程度（1-10分）
  subjective_feeling: string;   // 主观感受
  training_records: Array<{
    exercise_name: string;      // 动作名称
    sets: number;               // 组数
    reps: number;               // 次数
    weight: number;             // 重量（kg）
    notes?: string;             // 备注
  }>;
  created_at: string;           // 创建时间
}
```

---

## MCP工具接口

| 工具 | 功能 | 必需参数 |
|------|------|----------|
| `create_user_profile` | 创建用户档案 | user_id |
| `get_user_profile` | 获取用户档案 | user_id |
| `update_user_profile` | 更新用户档案 | user_id |
| `delete_user_profile` | 删除用户档案 | user_id |
| `list_user_profiles` | 列出所有档案 | 无 |
| `sync_from_frontend` | 前端同步 | user_id, frontend_data |
| `export_user_data` | 导出数据 | user_id |
| `clear_session_data` | 清除会话 | user_id |

---

## 数据存储

### 主存储：PHP后端MySQL
- 端点：`http://localhost:8000/api/internal/user-profile/{user_id}`
- 认证：`X-Internal-Token: crewai-internal-secret-2025`

### 备份存储：本地JSON文件
- 位置：`mcp-servers/user-profile-stdio/data/{user_id}.json`

### 会话存储：内存Map
- TTL：1小时（自动清理）
- 键格式：`{user_id}_{session_id}`

---

## 数据流转

```
前端localStorage
    ↓ (sync_from_frontend)
MCP会话存储（1小时TTL）
    ↓ (get_user_profile)
DAML-RAG工作流
    ↓ (MCP工具调用)
训练计划生成
    ↓
返回给用户
```

---

## 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v2.4.0 | 2025-12-23 | 混合方案实施，三层缓存 |
| v2.3.0 | 2025-12-20 | 新增TrainingFeedback |
| v2.2.0 | 2025-12-19 | 新增preferred_rest_pattern |
| v2.1.0 | 2025-12-19 | 前端集成工具 |
| v2.0.0 | 2025-10-24 | PHP后端集成 |
| v1.0.0 | 2025-08-01 | 初始版本 |

---

## 相关文档

- [MCP工具架构](../03-编排层/06-MCP工具架构.md)
- [MySQL数据结构](./04-MySQL数据结构.md)
- [用户档案数据映射](./03-用户档案数据映射.md)

---

**维护者**：薛小川  
**最后更新**：2025-12-20
