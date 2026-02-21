# MySQL数据结构

**版本**: v2.0.0  
**创建日期**: 2025-12-21  
**更新日期**: 2025-12-26  
**状态**: ✅ 已完成

---

## 概述

MySQL是玉珍健身应用的关系数据库，负责存储用户数据、训练记录、会话历史等业务数据。作为Layer 3业务规则约束层的核心，MySQL提供事务支持和数据一致性保证。

**v2.0.0更新**：新增闭环学习系统相关表（training_logs、personal_bests、chinese_holidays），扩展users表字段支持个性化容量调整。

**数据库名称**: `fitness_app`  
**字符集**: utf8mb4  
**排序规则**: utf8mb4_unicode_ci

---

## 核心表结构

### 1. users表 - 用户基本信息

#### 表结构

```sql
CREATE TABLE users (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(255) NULL,
    avatar VARCHAR(255) NULL,
    role VARCHAR(255) DEFAULT 'user',
    status CHAR(1) DEFAULT '1' COMMENT '状态：1正常/0禁用',
    del_flag CHAR(1) DEFAULT '0' COMMENT '删除标志：0未删/1已删',
    is_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMP NULL,
    membership_tier VARCHAR(255) DEFAULT 'newbie' COMMENT '会员等级',
    preferences JSON NULL COMMENT '用户偏好设置',
    favorites JSON NULL COMMENT '收藏的动作ID列表',
    exercise_reviews JSON NULL COMMENT '动作评价',
    email_verified_at TIMESTAMP NULL,
    onboarding_completed BOOLEAN DEFAULT FALSE COMMENT '是否完成引导',
    profile_completed_at TIMESTAMP NULL COMMENT '档案完成时间',
    password VARCHAR(255) NOT NULL,
    remember_token VARCHAR(100) NULL,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL,
    INDEX idx_email (email),
    INDEX idx_membership_tier (membership_tier)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### 字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `id` | BIGINT | 用户ID（主键） | 1 |
| `name` | VARCHAR(255) | 用户名 | "张三" |
| `email` | VARCHAR(255) | 邮箱（唯一） | "zhangsan@example.com" |
| `phone` | VARCHAR(255) | 手机号 | "13800138000" |
| `avatar` | VARCHAR(255) | 头像URL | "/avatars/user1.jpg" |
| `role` | VARCHAR(255) | 角色 | "user" / "admin" |
| `status` | CHAR(1) | 状态 | "1"正常 / "0"禁用 |
| `del_flag` | CHAR(1) | 删除标志 | "0"未删 / "1"已删 |
| `is_active` | BOOLEAN | 是否激活 | true |
| `last_login_at` | TIMESTAMP | 最后登录时间 | "2025-12-21 10:00:00" |
| `membership_tier` | VARCHAR(255) | 会员等级 | "newbie" / "bronze" / "silver" / "gold" |
| `preferences` | JSON | 用户偏好设置 | {"theme": "dark", "language": "zh"} |
| `favorites` | JSON | 收藏的动作ID列表 | [1, 5, 10, 23] |
| `exercise_reviews` | JSON | 动作评价 | {"1": {"rating": 5, "comment": "很好"}} |
| `onboarding_completed` | BOOLEAN | 是否完成引导 | false |
| `profile_completed_at` | TIMESTAMP | 档案完成时间 | "2025-12-21 10:00:00" |

#### ✨ v2.0.0新增字段（闭环学习系统）

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `personal_volume_multiplier` | DECIMAL(3,2) | 个性化容量系数(0.7-1.5) | 1.00 |
| `personal_recovery_factor` | DECIMAL(3,2) | 个性化恢复系数 | 1.00 |
| `last_volume_adjusted_at` | TIMESTAMP | 上次容量调整时间 | "2025-12-26 10:00:00" |
| `consecutive_training_weeks` | INT | 连续训练周数 | 4 |
| `preferred_training_time` | VARCHAR(50) | 时间偏好 | "晚间" |
| `body_type` | ENUM | 体型分类 | "normal" |
| `user_type` | ENUM | 用户类型 | "student" / "worker" / "other" |
| `campus_name` | VARCHAR(100) | 学校名称（大学生用户） | "清华大学" |

---

### 2. user_profiles表 - 用户档案（JSON结构）

#### 表结构

```sql
CREATE TABLE user_profiles (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED UNIQUE NOT NULL COMMENT '用户ID',
    basic_info JSON NULL COMMENT '基础信息：age, gender, height, weight等',
    fitness_goals JSON NULL COMMENT '健身目标：primary_goals, target_weight等',
    training_preferences JSON NULL COMMENT '训练偏好：training_split, available_equipment等',
    health_status JSON NULL COMMENT '健康状况：injuries, chronic_diseases等',
    nutrition_profile JSON NULL COMMENT '营养档案：daily_calories, protein_intake等',
    strength_data JSON NULL COMMENT '力量数据：bench_press, squat, deadlift等',
    ffmi_assessment JSON NULL COMMENT 'FFMI评估：ffmi, bmi, assessment等',
    version INT DEFAULT 1 COMMENT '数据版本号',
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL,
    last_sync_at TIMESTAMP NULL COMMENT '最后同步时间',
    sync_status VARCHAR(50) DEFAULT 'synced' COMMENT '同步状态',
    is_mcp_temp BOOLEAN DEFAULT FALSE COMMENT '是否为MCP临时数据',
    mcp_session_id VARCHAR(100) NULL COMMENT 'MCP会话ID',
    sync_source VARCHAR(50) NULL COMMENT '同步来源',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_sync_status (sync_status),
    INDEX idx_is_mcp_temp (is_mcp_temp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### JSON字段格式

**basic_info**（基础信息）:
```json
{
    "age": 25,
    "gender": "male",
    "height": 175,
    "weight": 70,
    "body_fat_percentage": 15.5
}
```

**fitness_goals**（健身目标）:
```json
{
    "primary_goals": ["增肌", "提高力量"],
    "target_weight": 75,
    "target_body_fat": 12,
    "timeline_weeks": 12
}
```

**training_preferences**（训练偏好）:
```json
{
    "training_split": "push_pull_legs",
    "available_equipment": ["哑铃", "杠铃", "卧推凳"],
    "training_days_per_week": 4,
    "preferred_training_time": "晚上"
}
```

**health_status**（健康状况）:
```json
{
    "injuries": ["膝盖受伤"],
    "chronic_diseases": [],
    "medications": [],
    "allergies": []
}
```

**nutrition_profile**（营养档案）:
```json
{
    "daily_calories": 2500,
    "protein_intake": 150,
    "carbs_intake": 300,
    "fat_intake": 70,
    "dietary_restrictions": ["素食"]
}
```

**strength_data**（力量数据）:
```json
{
    "bench_press": {"weight": 60, "reps": 10, "date": "2025-12-21"},
    "squat": {"weight": 100, "reps": 8, "date": "2025-12-21"},
    "deadlift": {"weight": 120, "reps": 5, "date": "2025-12-21"}
}
```

**ffmi_assessment**（FFMI评估）:
```json
{
    "ffmi": 20.5,
    "bmi": 22.9,
    "assessment": "良好",
    "calculated_at": "2025-12-21"
}
```

#### 使用场景

1. **用户档案预加载**（步骤1）
   - 工作流程开始时加载用户完整档案
   - 提供给MCP工具使用

2. **MCP服务同步**
   - `is_mcp_temp`: 标记MCP临时数据
   - `mcp_session_id`: 关联MCP会话
   - `sync_status`: 跟踪同步状态

---

### 3. chat_sessions表 - 对话会话

#### 表结构

```sql
CREATE TABLE chat_sessions (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id CHAR(36) NOT NULL COMMENT '会话UUID，支持多轮对话',
    user_id BIGINT UNSIGNED NULL COMMENT '用户ID（匿名用户为NULL）',
    user_query TEXT NOT NULL COMMENT '用户问题',
    llm_response TEXT NOT NULL COMMENT 'AI回答',
    model_used VARCHAR(50) NOT NULL COMMENT '使用的模型（deepseek-chat/anthropic-claude-qwen3:8b）',
    tools_used JSON NULL COMMENT '调用的工具列表（JSON数组）',
    metadata JSON NULL COMMENT '元数据：few_shot_count, orchestrator_used等',
    user_rating TINYINT NULL COMMENT '用户评分（1-5星）',
    user_feedback VARCHAR(500) NULL COMMENT '用户反馈',
    qdrant_point_id CHAR(36) NULL COMMENT 'Qdrant向量点ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_session_id (session_id),
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at),
    INDEX idx_model_used (model_used),
    INDEX idx_qdrant_point_id (qdrant_point_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### 字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `id` | BIGINT | 记录ID（主键） | 1 |
| `session_id` | CHAR(36) | 会话UUID | "550e8400-e29b-41d4-a716-446655440000" |
| `user_id` | BIGINT | 用户ID（可为NULL） | 1 |
| `user_query` | TEXT | 用户查询 | "推荐胸部训练动作" |
| `llm_response` | TEXT | AI响应 | "推荐以下动作..." |
| `model_used` | VARCHAR(50) | 使用的模型 | "deepseek-chat" |
| `tools_used` | JSON | 使用的工具 | ["get_exercises", "design_program"] |
| `metadata` | JSON | 元数据 | {"few_shot_count": 3, "orchestrator": "dag"} |
| `user_rating` | TINYINT | 用户评分（1-5） | 5 |
| `user_feedback` | VARCHAR(500) | 用户反馈 | "很有帮助" |
| `qdrant_point_id` | CHAR(36) | Qdrant向量ID | "..." |

#### JSON字段格式

**tools_used**:
```json
["get_user_profile", "get_exercises", "design_program"]
```

**metadata**:
```json
{
    "few_shot_count": 3,
    "orchestrator_used": "dag",
    "execution_time_ms": 1500,
    "model_temperature": 0.7
}
```

#### 使用场景

1. **Few-Shot检索**（步骤6）
   - 检索高评分对话（rating≥4.0）
   - 同步到Qdrant的`chat_sessions_fewshot`集合

2. **对话历史追踪**
   - 通过`session_id`追踪多轮对话
   - 支持匿名用户（user_id为NULL）

3. **质量评估**
   - 用户评分和反馈
   - 用于数据清洗和模型微调

---

### 4. training_plans表 - 训练计划

#### 表结构

```sql
CREATE TABLE training_plans (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
    name VARCHAR(255) NOT NULL COMMENT '计划名称',
    name_zh VARCHAR(255) NULL COMMENT '计划名称（中文）',
    description TEXT NULL COMMENT '计划描述',
    goal ENUM('lose_weight', 'gain_muscle', 'maintain', 'improve_fitness') NULL COMMENT '训练目标',
    difficulty ENUM('beginner', 'intermediate', 'advanced') NULL COMMENT '难度',
    duration_weeks INT DEFAULT 4 COMMENT '总周数',
    workouts_per_week INT DEFAULT 3 COMMENT '每周训练次数',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    started_at DATETIME NULL COMMENT '开始时间',
    completed_at DATETIME NULL COMMENT '完成时间',
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_active (user_id, is_active),
    INDEX idx_goal (goal)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### 字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `id` | BIGINT | 计划ID（主键） | 1 |
| `user_id` | BIGINT | 用户ID | 1 |
| `name` | VARCHAR(255) | 计划名称 | "12-Week Muscle Gain" |
| `name_zh` | VARCHAR(255) | 中文名称 | "12周增肌计划" |
| `description` | TEXT | 计划描述 | "适合中级训练者..." |
| `goal` | ENUM | 训练目标 | "gain_muscle" |
| `difficulty` | ENUM | 难度 | "intermediate" |
| `duration_weeks` | INT | 总周数 | 12 |
| `workouts_per_week` | INT | 每周训练次数 | 4 |
| `is_active` | BOOLEAN | 是否激活 | true |
| `started_at` | DATETIME | 开始时间 | "2025-12-21 00:00:00" |
| `completed_at` | DATETIME | 完成时间 | NULL |

---

### 5. training_sessions表 - 训练会话

#### 表结构

```sql
CREATE TABLE training_sessions (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    plan_id BIGINT UNSIGNED NULL COMMENT '关联的训练计划ID',
    session_name VARCHAR(255) NOT NULL COMMENT '训练名称',
    notes TEXT NULL COMMENT '训练笔记',
    duration_minutes INT NULL COMMENT '训练时长（分钟）',
    status ENUM('pending', 'in_progress', 'completed', 'skipped') DEFAULT 'pending',
    started_at DATETIME NULL,
    completed_at DATETIME NULL,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES training_plans(id) ON DELETE SET NULL,
    INDEX idx_user_status (user_id, status),
    INDEX idx_completed_at (completed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### 字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `id` | BIGINT | 会话ID（主键） | 1 |
| `user_id` | BIGINT | 用户ID | 1 |
| `plan_id` | BIGINT | 训练计划ID | 1 |
| `session_name` | VARCHAR(255) | 训练名称 | "胸部训练" |
| `notes` | TEXT | 训练笔记 | "感觉良好，重量有提升" |
| `duration_minutes` | INT | 训练时长（分钟） | 60 |
| `status` | ENUM | 状态 | "completed" |
| `started_at` | DATETIME | 开始时间 | "2025-12-21 18:00:00" |
| `completed_at` | DATETIME | 完成时间 | "2025-12-21 19:00:00" |

---

### 6. training_records表 - 训练记录

#### 表结构

```sql
CREATE TABLE training_records (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id BIGINT UNSIGNED NOT NULL COMMENT '训练会话ID',
    exercise_id BIGINT UNSIGNED NOT NULL COMMENT '动作ID',
    set_number INT NOT NULL COMMENT '组数',
    reps INT NOT NULL COMMENT '次数',
    weight DECIMAL(8,2) NULL COMMENT '重量（kg）',
    rpe INT NULL COMMENT 'RPE（1-10）',
    rest_seconds INT NULL COMMENT '组间休息（秒）',
    notes TEXT NULL COMMENT '备注',
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL,
    FOREIGN KEY (session_id) REFERENCES training_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE,
    INDEX idx_session_id (session_id),
    INDEX idx_exercise_id (exercise_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### 字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `id` | BIGINT | 记录ID（主键） | 1 |
| `session_id` | BIGINT | 训练会话ID | 1 |
| `exercise_id` | BIGINT | 动作ID | 1 |
| `set_number` | INT | 组数 | 1 |
| `reps` | INT | 次数 | 10 |
| `weight` | DECIMAL(8,2) | 重量（kg） | 60.00 |
| `rpe` | INT | RPE（1-10） | 8 |
| `rest_seconds` | INT | 组间休息（秒） | 90 |
| `notes` | TEXT | 备注 | "最后一组力竭" |

#### 使用场景

1. **训练历史查询**
   - 查询用户的训练记录
   - 分析训练进度

2. **力量进步追踪**
   - 追踪某个动作的重量变化
   - 计算力量增长率

3. **训练量统计**
   - 统计每周训练量
   - 分析训练频率

---

## ✨ v2.0.0新增表（闭环学习系统）

### 7. training_logs表 - 训练日志（闭环学习核心）

**用途**：记录用户每次训练的详细数据，支持闭环学习系统的数据分析。

#### 表结构

```sql
CREATE TABLE training_logs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
    session_date DATE NOT NULL COMMENT '训练日期',
    planned_exercises JSON COMMENT '计划动作列表',
    actual_exercises JSON COMMENT '实际完成情况',
    completion_rate DECIMAL(3,2) COMMENT '完成率(0-1)',
    avg_rpe DECIMAL(3,1) COMMENT '平均RPE(1-10)',
    notes TEXT COMMENT '备注',
    mesocycle_id VARCHAR(50) NULL COMMENT '中周期ID',
    week_number INT NULL COMMENT '周期内周数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_date (user_id, session_date),
    INDEX idx_session_date (session_date),
    INDEX idx_mesocycle (mesocycle_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='训练日志表';
```

#### 字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `id` | BIGINT | 日志ID（主键） | 1 |
| `user_id` | BIGINT | 用户ID | 1 |
| `session_date` | DATE | 训练日期 | "2025-12-26" |
| `planned_exercises` | JSON | 计划动作列表 | 见下方JSON格式 |
| `actual_exercises` | JSON | 实际完成情况 | 见下方JSON格式 |
| `completion_rate` | DECIMAL(3,2) | 完成率(0-1) | 0.95 |
| `avg_rpe` | DECIMAL(3,1) | 平均RPE(1-10) | 7.5 |
| `notes` | TEXT | 备注 | "今天状态不错" |
| `mesocycle_id` | VARCHAR(50) | 中周期ID | "meso_2025_01" |
| `week_number` | INT | 周期内周数 | 2 |

#### JSON字段格式

**planned_exercises**（计划动作）:
```json
[
    {
        "exercise_id": "EX001",
        "name_zh": "杠铃深蹲",
        "planned_sets": 4,
        "planned_reps": 8,
        "planned_weight": 100
    }
]
```

**actual_exercises**（实际完成）:
```json
[
    {
        "exercise_id": "EX001",
        "name_zh": "杠铃深蹲",
        "sets": [
            {"reps": 8, "weight": 100, "rpe": 7},
            {"reps": 8, "weight": 100, "rpe": 8},
            {"reps": 7, "weight": 100, "rpe": 9},
            {"reps": 6, "weight": 100, "rpe": 10}
        ],
        "completed_sets": 4,
        "avg_rpe": 8.5
    }
]
```

#### 使用场景

1. **闭环学习分析**（Requirements 7.1）
   - TrainingLogAnalyzer读取训练日志
   - 分析完成率趋势和RPE趋势
   - 为容量调整提供数据支持

2. **中周期分析**
   - 按mesocycle_id分组分析
   - 计算4-6周的训练表现

3. **分周计划生成**（Requirements 10.3, 10.4）
   - 基于上周反馈生成下周计划
   - 动态调整训练容量

---

### 8. personal_bests表 - 个人最佳记录

**用途**：记录用户各动作的个人最佳成绩，支持渐进过载计算。

#### 表结构

```sql
CREATE TABLE personal_bests (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
    exercise_id VARCHAR(50) NOT NULL COMMENT 'Neo4j Exercise节点ID',
    best_weight DECIMAL(5,2) COMMENT '最佳重量(kg)',
    best_reps INT COMMENT '最佳次数',
    achieved_date DATE COMMENT '达成日期',
    last_used_weight DECIMAL(5,2) COMMENT '上次使用重量',
    last_used_date DATE COMMENT '上次使用日期',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uk_user_exercise (user_id, exercise_id),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='个人最佳记录表';
```

#### 字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `id` | BIGINT | 记录ID（主键） | 1 |
| `user_id` | BIGINT | 用户ID | 1 |
| `exercise_id` | VARCHAR(50) | Neo4j Exercise节点ID | "EX001" |
| `best_weight` | DECIMAL(5,2) | 最佳重量(kg) | 120.00 |
| `best_reps` | INT | 最佳次数 | 8 |
| `achieved_date` | DATE | 达成日期 | "2025-12-20" |
| `last_used_weight` | DECIMAL(5,2) | 上次使用重量 | 115.00 |
| `last_used_date` | DATE | 上次使用日期 | "2025-12-26" |

#### 使用场景

1. **渐进过载计算**（Requirements 8.1, 8.2）
   - 计算下周建议重量
   - 检测重量下降（回归检测）

2. **个人记录追踪**（Requirements 6.4）
   - 自动更新个人最佳记录
   - 显示进步历程

---

### 9. chinese_holidays表 - 中国节假日配置

**用途**：存储中国节假日信息，用于训练计划的节假日调整。

#### 表结构

```sql
CREATE TABLE chinese_holidays (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    holiday_name VARCHAR(50) NOT NULL COMMENT '节假日名称',
    start_date DATE NOT NULL COMMENT '开始日期',
    end_date DATE NOT NULL COMMENT '结束日期',
    holiday_type ENUM('spring_festival', 'national_day', 'labor_day', 'mid_autumn', 'qingming', 'dragon_boat', 'other') COMMENT '节假日类型',
    year INT NOT NULL COMMENT '年份',
    is_workday BOOLEAN DEFAULT FALSE COMMENT '是否为调休工作日',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_year (year),
    INDEX idx_dates (start_date, end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='中国节假日配置表';
```

#### 字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `id` | INT | 记录ID（主键） | 1 |
| `holiday_name` | VARCHAR(50) | 节假日名称 | "春节" |
| `start_date` | DATE | 开始日期 | "2026-01-28" |
| `end_date` | DATE | 结束日期 | "2026-02-03" |
| `holiday_type` | ENUM | 节假日类型 | "spring_festival" |
| `year` | INT | 年份 | 2026 |
| `is_workday` | BOOLEAN | 是否为调休工作日 | false |

#### 使用场景

1. **训练计划调整**
   - 节假日期间调整训练安排
   - 提供节假日训练建议

2. **中国本地化**（Requirements 2.1）
   - 支持"练五休二"等中国特色休息模式
   - 适配中国用户的作息习惯

---

## 数据库关系图

```
users (1) ─────┬───── (1) user_profiles
               │
               ├───── (N) chat_sessions
               │
               ├───── (N) training_plans
               │
               ├───── (N) training_sessions
               │           │
               │           └───── (N) training_records
               │                       │
               │                       └───── (1) exercises
               │
               ├───── (N) training_logs      ← v2.0.0新增
               │
               └───── (N) personal_bests     ← v2.0.0新增
```

---

## 索引策略

### 主要索引

| 表 | 索引 | 类型 | 用途 |
|------|------|------|------|
| users | idx_email | UNIQUE | 邮箱查询 |
| users | idx_membership_tier | INDEX | 会员等级查询 |
| user_profiles | idx_sync_status | INDEX | 同步状态查询 |
| chat_sessions | idx_session_id | INDEX | 会话查询 |
| chat_sessions | idx_user_id | INDEX | 用户对话历史 |
| chat_sessions | idx_created_at | INDEX | 时间范围查询 |
| training_sessions | idx_user_status | COMPOSITE | 用户训练状态 |
| training_records | idx_session_id | INDEX | 会话记录查询 |
| training_logs | idx_user_date | COMPOSITE | 用户训练日志查询 |
| training_logs | idx_mesocycle | INDEX | 中周期分析 |
| personal_bests | uk_user_exercise | UNIQUE | 用户动作最佳记录 |
| chinese_holidays | idx_year | INDEX | 年份查询 |

---

## 常用查询示例

### 1. 查询用户完整档案

```sql
SELECT 
    u.id,
    u.name,
    u.email,
    u.membership_tier,
    up.basic_info,
    up.fitness_goals,
    up.training_preferences,
    up.health_status
FROM users u
LEFT JOIN user_profiles up ON u.id = up.user_id
WHERE u.id = 1;
```

### 2. 查询高质量对话（Few-Shot）

```sql
SELECT 
    session_id,
    user_query,
    llm_response,
    tools_used,
    user_rating
FROM chat_sessions
WHERE user_rating >= 4.0
    AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
ORDER BY created_at DESC
LIMIT 10;
```

### 3. 查询用户训练历史

```sql
SELECT 
    ts.session_name,
    ts.completed_at,
    e.name AS exercise_name,
    tr.set_number,
    tr.reps,
    tr.weight,
    tr.rpe
FROM training_sessions ts
JOIN training_records tr ON ts.id = tr.session_id
JOIN exercises e ON tr.exercise_id = e.id
WHERE ts.user_id = 1
    AND ts.status = 'completed'
    AND ts.completed_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
ORDER BY ts.completed_at DESC, tr.set_number ASC;
```

### 4. 统计训练量

```sql
SELECT 
    DATE_FORMAT(ts.completed_at, '%Y-%m') AS month,
    COUNT(DISTINCT ts.id) AS total_sessions,
    SUM(tr.reps * tr.weight) AS total_volume
FROM training_sessions ts
JOIN training_records tr ON ts.id = tr.session_id
WHERE ts.user_id = 1
    AND ts.status = 'completed'
GROUP BY month
ORDER BY month DESC;
```

### 5. 查询用户训练日志（闭环学习）

```sql
-- 获取用户最近4周的训练日志（用于中周期分析）
SELECT 
    id,
    session_date,
    completion_rate,
    avg_rpe,
    mesocycle_id,
    week_number
FROM training_logs
WHERE user_id = 1
    AND session_date >= DATE_SUB(CURDATE(), INTERVAL 28 DAY)
ORDER BY session_date DESC;
```

### 6. 查询个人最佳记录

```sql
-- 获取用户某动作的个人最佳记录
SELECT 
    pb.exercise_id,
    pb.best_weight,
    pb.best_reps,
    pb.achieved_date,
    pb.last_used_weight,
    pb.last_used_date
FROM personal_bests pb
WHERE pb.user_id = 1
    AND pb.exercise_id = 'EX001';
```

### 7. 分析完成率趋势

```sql
-- 分析用户最近4周的完成率趋势
SELECT 
    WEEK(session_date) AS week_num,
    AVG(completion_rate) AS avg_completion,
    AVG(avg_rpe) AS avg_rpe,
    COUNT(*) AS session_count
FROM training_logs
WHERE user_id = 1
    AND session_date >= DATE_SUB(CURDATE(), INTERVAL 28 DAY)
GROUP BY week_num
ORDER BY week_num;
```

---

## 性能监控

### 关键指标

| 指标 | 目标值 | 监控方法 |
|------|--------|---------|
| 查询响应时间 | <100ms | slow_query_log |
| 连接数 | <100 | SHOW STATUS |
| 表大小 | <10GB | information_schema |
| 索引命中率 | >95% | EXPLAIN分析 |

### 慢查询优化

**启用慢查询日志**:
```sql
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;
```

**分析慢查询**:
```bash
mysqldumpslow -s t -t 10 /var/log/mysql/slow-query.log
```

---

## 备份策略

### 备份方案

**每日全量备份**:
```bash
mysqldump -u root -p fitness_app > backup/fitness_app_$(date +%Y%m%d).sql
```

**binlog增量备份**:
```bash
mysqlbinlog --start-datetime="2025-12-21 00:00:00" \
            --stop-datetime="2025-12-21 23:59:59" \
            /var/log/mysql/mysql-bin.000001 > backup/incremental.sql
```

### 恢复流程

**恢复全量备份**:
```bash
mysql -u root -p fitness_app < backup/fitness_app_20251221.sql
```

**恢复增量备份**:
```bash
mysql -u root -p fitness_app < backup/incremental.sql
```

---

## 相关文档

- [Neo4j数据库结构](./02-Neo4j数据库结构.md)
- [Qdrant向量库结构](./03-Qdrant向量库结构.md)
- [数据库结构总览](./01-数据库结构总览.md)
- [用户档案MCP数据结构](./05-用户档案MCP数据结构.md)

---

**维护者**: 薛小川  
**最后更新**: 2025-12-26
