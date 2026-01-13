#!/usr/bin/env node
/**
 * User Profile MCP Server (stdio version) v2.0
 *
 * 增强的用户档案管理服务 - 集成营养指南字段
 *
 * 核心功能：
 * 1. create_user_profile - 创建用户档案
 * 2. get_user_profile - 获取用户档案
 * 3. update_user_profile - 更新用户档案
 * 4. delete_user_profile - 删除用户档案
 * 5. list_user_profiles - 列出所有用户档案
 *
 * 新增营养指南字段：
 * - region: 地区（华北、东北、华东、华南、西南、西北、华中）
 * - population: 人群类型（孕妇、乳母、婴幼儿、儿童青少年、老年人、素食人群）
 * - age_gender_group: 年龄性别组
 * - dietary_preferences: 饮食偏好
 * - allergies: 过敏食物
 */
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema, } from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";
import axios from "axios";
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
// =============================================================================
// PHP后端配置
// =============================================================================
const PHP_BACKEND_URL = process.env.PHP_BACKEND_URL || "http://localhost:8000";
const PHP_INTERNAL_TOKEN = process.env.PHP_INTERNAL_TOKEN || "crewai-internal-secret-2025";
// HTTP客户端配置
const phpClient = axios.create({
    baseURL: PHP_BACKEND_URL,
    timeout: 10000,
    headers: {
        "Content-Type": "application/json",
        "X-Internal-Token": PHP_INTERNAL_TOKEN,
    },
});
// =============================================================================
// 用户档案管理器
// =============================================================================
class UserProfileManager {
    dataDir;
    sessionStorage; // 会话存储
    constructor() {
        // 编译后代码在 build/index.js，向上一级到达项目根目录，再进入 data/
        this.dataDir = path.join(__dirname, "..", "data");
        this.sessionStorage = new Map();
        this.ensureDataDir();
        // 自动清理过期会话（1小时TTL）
        setInterval(() => this.cleanExpiredSessions(), 60 * 60 * 1000);
    }
    // 清理过期会话
    cleanExpiredSessions() {
        const now = Date.now();
        const oneHour = 60 * 60 * 1000;
        for (const [key, value] of this.sessionStorage.entries()) {
            const sessionTime = new Date(value.timestamp).getTime();
            if (now - sessionTime > oneHour) {
                this.sessionStorage.delete(key);
                console.error(`🗑️  已清理过期会话: ${key}`);
            }
        }
    }
    ensureDataDir() {
        if (!fs.existsSync(this.dataDir)) {
            fs.mkdirSync(this.dataDir, { recursive: true });
            console.error("✅ 用户档案数据目录已创建");
        }
    }
    getProfilePath(userId) {
        return path.join(this.dataDir, `${userId}.json`);
    }
    // 计算BMI
    calculateBMI(height, weight) {
        if (height && weight) {
            const heightM = height / 100;
            return parseFloat((weight / (heightM ** 2)).toFixed(1));
        }
        return null;
    }
    // 计算FFMI
    calculateFFMI(height, weight, bodyFat) {
        if (height && weight && bodyFat) {
            const leanMass = weight * (1 - bodyFat / 100);
            const heightM = height / 100;
            return parseFloat((leanMass / (heightM ** 2)).toFixed(2));
        }
        return null;
    }
    // 创建用户档案
    createProfile(userId, profileData) {
        const profilePath = this.getProfilePath(userId);
        if (fs.existsSync(profilePath)) {
            throw new Error(`用户档案已存在: ${userId}`);
        }
        const profile = {
            user_id: userId,
            basic_info: profileData.basic_info || {},
            nutrition_profile: profileData.nutrition_profile || {},
            fitness_config: profileData.fitness_config || {},
            fitness_goals: profileData.fitness_goals || {},
            strength_levels: profileData.strength_levels || {},
            health_profile: profileData.health_profile || {},
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
        };
        fs.writeFileSync(profilePath, JSON.stringify(profile, null, 2), "utf-8");
        console.error(`✅ 用户档案已创建: ${userId}`);
        return profile;
    }
    // 获取用户档案（从PHP后端）
    async getProfile(userId) {
        try {
            // 调用PHP后端API
            const response = await phpClient.get(`/api/internal/user-profile/${userId}`);
            if (!response.data.success) {
                throw new Error(response.data.message || "获取用户档案失败");
            }
            const phpProfile = response.data.data;
            // ✅ 转换PHP后端数据格式到MCP格式（2025-12-20更新）
            // PHP后端现在返回嵌套结构（basic_info, fitness_goals等）
            const profile = {
                user_id: userId,
                basic_info: {
                    age: phpProfile.basic_info?.age,
                    gender: phpProfile.basic_info?.gender,
                    height: phpProfile.basic_info?.height,
                    weight: phpProfile.basic_info?.weight,
                    body_fat_percentage: phpProfile.basic_info?.body_fat_percentage,
                    bmi: phpProfile.basic_info?.bmi,
                    ffmi: phpProfile.ffmi_assessment?.ffmi,
                },
                nutrition_profile: {
                    region: phpProfile.basic_info?.region,
                    population: phpProfile.nutrition_profile?.user_settings?.population,
                    dietary_preferences: phpProfile.nutrition_profile?.user_settings?.dietary_preferences || [],
                    allergies: phpProfile.nutrition_profile?.user_settings?.allergies || [],
                    supplements: phpProfile.nutrition_profile?.user_settings?.supplements || [],
                    budget_level: phpProfile.nutrition_profile?.user_settings?.budget_level,
                    daily_calorie_target: phpProfile.nutrition_profile?.auto_calculated?.tdee,
                    daily_protein_target: phpProfile.nutrition_profile?.auto_calculated?.protein_target,
                    meal_frequency: phpProfile.nutrition_profile?.user_settings?.meal_frequency,
                },
                fitness_config: {
                    training_experience_months: phpProfile.training_experience_months,
                    fitness_level: phpProfile.basic_info?.fitness_level,
                    preferred_training_split: phpProfile.fitness_goals?.training_split,
                    preferred_rest_pattern: phpProfile.training_preferences?.preferred_rest_pattern,
                    training_days_per_week: phpProfile.training_preferences?.training_days,
                    training_duration_per_session: phpProfile.training_duration_per_session,
                    training_location: phpProfile.training_preferences?.training_location,
                    exercise_preferences: phpProfile.training_preferences?.exercise_preferences || [],
                    disliked_exercises: phpProfile.training_preferences?.disliked_exercises || [],
                    sleep_hours: phpProfile.basic_info?.sleep_hours,
                },
                fitness_goals: {
                    primary_goal: phpProfile.fitness_goals?.primary_goals?.[0],
                    target_weight: phpProfile.fitness_goals?.target_weight,
                    secondary_goals: phpProfile.fitness_goals?.secondary_goals || [],
                },
                strength_levels: phpProfile.strength_data || {
                    squat_1rm: null,
                    bench_press_1rm: null,
                    deadlift_1rm: null,
                },
                health_profile: {
                    injury_history: phpProfile.health_status?.injury_history || [],
                    health_conditions: phpProfile.health_status?.chronic_diseases || [],
                    medications: phpProfile.health_status?.medications || [],
                },
                training_feedback: phpProfile.training_feedback || [],
                created_at: phpProfile.created_at,
                updated_at: phpProfile.updated_at,
            };
            console.error(`✅ 从PHP后端获取用户档案: ${userId}`);
            return profile;
        }
        catch (error) {
            console.error(`❌ 获取用户档案失败: ${userId}`, error.message);
            // 降级：使用本地JSON文件（如果存在）
            const profilePath = this.getProfilePath(userId);
            if (fs.existsSync(profilePath)) {
                console.error(`⚠️ 降级到本地JSON文件: ${userId}`);
                const content = fs.readFileSync(profilePath, "utf-8");
                return JSON.parse(content);
            }
            throw new Error(`用户档案不存在: ${userId}`);
        }
    }
    // 更新用户档案（暂时保留本地实现，未来可改为调用PHP API）
    async updateProfile(userId, updates) {
        const profilePath = this.getProfilePath(userId);
        if (!fs.existsSync(profilePath)) {
            throw new Error(`用户档案不存在: ${userId}`);
        }
        const content = fs.readFileSync(profilePath, "utf-8");
        const existingProfile = JSON.parse(content);
        const updatedProfile = {
            ...existingProfile,
            basic_info: { ...existingProfile.basic_info, ...updates.basic_info },
            nutrition_profile: { ...existingProfile.nutrition_profile, ...updates.nutrition_profile },
            fitness_config: { ...existingProfile.fitness_config, ...updates.fitness_config },
            fitness_goals: { ...existingProfile.fitness_goals, ...updates.fitness_goals },
            strength_levels: { ...existingProfile.strength_levels, ...updates.strength_levels },
            updated_at: new Date().toISOString(),
        };
        fs.writeFileSync(profilePath, JSON.stringify(updatedProfile, null, 2), "utf-8");
        console.error(`✅ 用户档案已更新: ${userId}`);
        return await this.getProfile(userId);
    }
    // 删除用户档案
    deleteProfile(userId) {
        const profilePath = this.getProfilePath(userId);
        if (!fs.existsSync(profilePath)) {
            throw new Error(`用户档案不存在: ${userId}`);
        }
        fs.unlinkSync(profilePath);
        console.error(`✅ 用户档案已删除: ${userId}`);
        return true;
    }
    // 列出所有用户档案
    listProfiles() {
        if (!fs.existsSync(this.dataDir)) {
            return [];
        }
        const files = fs.readdirSync(this.dataDir);
        return files
            .filter(file => file.endsWith(".json"))
            .map(file => file.replace(".json", ""));
    }
    // ============ 前端集成工具 ============
    // 从前端同步数据（会话存储）
    syncFromFrontend(userId, frontendData, syncMode = "full", sessionId) {
        // 生成或使用提供的session_id
        const finalSessionId = sessionId || `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const storageKey = `${userId}_${finalSessionId}`;
        // 获取同步的字段列表
        const syncedFields = Object.keys(frontendData);
        // 存储到会话存储
        if (syncMode === "full" || !this.sessionStorage.has(storageKey)) {
            // 全量同步
            this.sessionStorage.set(storageKey, {
                data: frontendData,
                timestamp: new Date().toISOString(),
                session_id: finalSessionId
            });
        }
        else {
            // 增量同步
            const existing = this.sessionStorage.get(storageKey);
            if (existing) {
                this.sessionStorage.set(storageKey, {
                    data: { ...existing.data, ...frontendData },
                    timestamp: new Date().toISOString(),
                    session_id: finalSessionId
                });
            }
        }
        console.error(`✅ 前端数据已同步到会话存储: ${userId} (session: ${finalSessionId})`);
        console.error(`   同步字段: ${syncedFields.join(", ")}`);
        return {
            status: "success",
            message: `成功同步${syncedFields.length}个字段到会话存储`,
            synced_fields: syncedFields,
            sync_timestamp: new Date().toISOString(),
            session_id: finalSessionId
        };
    }
    // 导出用户数据
    exportUserData(userId, format = "json", includeHistory = true) {
        // 尝试从持久化存储读取
        let userData = {};
        const profilePath = this.getProfilePath(userId);
        if (fs.existsSync(profilePath)) {
            const content = fs.readFileSync(profilePath, "utf-8");
            userData = JSON.parse(content);
        }
        // 合并会话存储中的数据（如果有）
        const sessionKeys = Array.from(this.sessionStorage.keys()).filter(key => key.startsWith(`${userId}_`));
        if (sessionKeys.length > 0) {
            console.error(`📦 发现${sessionKeys.length}个会话数据，合并导出`);
            sessionKeys.forEach(key => {
                const sessionData = this.sessionStorage.get(key);
                if (sessionData) {
                    userData = { ...userData, ...sessionData.data };
                }
            });
        }
        // 添加导出元数据
        const exportData = {
            ...userData,
            _export_metadata: {
                exported_at: new Date().toISOString(),
                user_id: userId,
                include_history: includeHistory,
                format: format
            }
        };
        console.error(`✅ 用户数据已导出: ${userId} (格式: ${format})`);
        return {
            status: "success",
            user_data: exportData,
            export_timestamp: new Date().toISOString(),
            data_version: "2.0.0",
            format: format
        };
    }
    // 清除会话数据
    clearSessionData(userId, sessionId) {
        const clearedSessions = [];
        if (sessionId) {
            // 清除指定会话
            const key = `${userId}_${sessionId}`;
            if (this.sessionStorage.has(key)) {
                this.sessionStorage.delete(key);
                clearedSessions.push(sessionId);
                console.error(`🗑️  已清除会话: ${key}`);
            }
        }
        else {
            // 清除该用户的所有会话
            const keysToDelete = Array.from(this.sessionStorage.keys()).filter(key => key.startsWith(`${userId}_`));
            keysToDelete.forEach(key => {
                const sessionData = this.sessionStorage.get(key);
                if (sessionData) {
                    clearedSessions.push(sessionData.session_id);
                }
                this.sessionStorage.delete(key);
            });
            console.error(`🗑️  已清除用户所有会话: ${userId} (共${keysToDelete.length}个)`);
        }
        return {
            status: "success",
            message: `成功清除${clearedSessions.length}个会话`,
            cleared_sessions: clearedSessions
        };
    }
}
// =============================================================================
// MCP服务器设置
// =============================================================================
const manager = new UserProfileManager();
const server = new Server({
    name: "user-profile-stdio",
    version: "2.1.0",
}, {
    capabilities: {
        tools: {},
    },
});
// 工具定义
const tools = [
    {
        name: "create_user_profile",
        description: `创建新的用户档案。
    
支持字段：
1. 基础信息 (basic_info):
   - age: 年龄
   - gender: 性别（男/女）
   - height: 身高(cm)
   - weight: 体重(kg)
   - body_fat_percentage: 体脂率(%)

2. 营养档案 (nutrition_profile):
   - region: 地区（华北地区、东北地区、华东地区、华南地区、西南地区、西北地区、华中地区）
   - population: 人群类型（孕妇、乳母、婴幼儿、儿童青少年、老年人、素食人群、普通成年人）
   - age_gender_group: 年龄性别组（成年男性(18-49岁)、成年女性(18-49岁)、老年人(65岁以上)）
   - dietary_preferences: 饮食偏好（数组）
   - allergies: 过敏食物（数组）
   - supplements: 补剂使用（蛋白粉、肌酸、BCAA等）  ✅ 新增
   - budget_level: 预算限制（low/moderate/high）  ✅ 新增
   - daily_calorie_target: 每日热量目标(kcal)（AI自动计算）
   - daily_protein_target: 每日蛋白质目标(g)（AI自动计算）
   - meal_frequency: 每日餐数

3. 健身配置 (fitness_config):
   - training_experience_months: 训练经验(月)
   - fitness_level: 健身水平
   - preferred_training_split: 训练分化
   - preferred_rest_pattern: 用户偏好的休息模式（练一休一、练二休一、练三休一等）  ✅ 新增
   - training_days_per_week: 每周训练天数
   - training_duration_per_session: 每次训练时长(分钟)
   - training_location: 训练场地（健身房/家里/户外/混合）  ✅ 新增
   - exercise_preferences: 运动偏好（自由重量、固定器械等）  ✅ 新增
   - disliked_exercises: 不喜欢的动作（避免的训练动作）  ✅ 新增
   - sleep_hours: 每晚睡眠小时数  ✅ 新增

4. 健身目标 (fitness_goals):
   - primary_goal: 主要目标
   - target_weight: 目标体重(kg)
   - secondary_goals: 次要目标（数组）

5. 力量水平 (strength_levels):
   - squat_1rm, bench_press_1rm, deadlift_1rm等`,
        inputSchema: {
            type: "object",
            properties: {
                user_id: {
                    type: "string",
                    description: "用户ID（唯一标识符）",
                },
                basic_info: {
                    type: "object",
                    description: "基础信息",
                },
                nutrition_profile: {
                    type: "object",
                    description: "营养档案（含地区、人群等信息）",
                },
                fitness_config: {
                    type: "object",
                    description: "健身配置",
                },
                fitness_goals: {
                    type: "object",
                    description: "健身目标",
                },
                strength_levels: {
                    type: "object",
                    description: "力量水平",
                },
            },
            required: ["user_id"],
        },
    },
    {
        name: "get_user_profile",
        description: `获取用户档案的完整信息。
    
返回数据包含：
- 基础信息（含自动计算的BMI和FFMI）
- 营养档案（地区、人群、饮食偏好等）
- 健身配置
- 健身目标
- 力量水平
- 创建和更新时间`,
        inputSchema: {
            type: "object",
            properties: {
                user_id: {
                    type: "string",
                    description: "用户ID",
                },
            },
            required: ["user_id"],
        },
    },
    {
        name: "update_user_profile",
        description: `更新用户档案的部分或全部信息。
    
支持增量更新，只需提供要更新的字段。
特别适用于：
- 更新体重、体脂等身体数据
- 更新地区、人群等营养相关信息
- 更新训练目标和计划
- 更新力量数据`,
        inputSchema: {
            type: "object",
            properties: {
                user_id: {
                    type: "string",
                    description: "用户ID",
                },
                basic_info: {
                    type: "object",
                    description: "要更新的基础信息",
                },
                nutrition_profile: {
                    type: "object",
                    description: "要更新的营养档案",
                },
                fitness_config: {
                    type: "object",
                    description: "要更新的健身配置",
                },
                fitness_goals: {
                    type: "object",
                    description: "要更新的健身目标",
                },
                strength_levels: {
                    type: "object",
                    description: "要更新的力量水平",
                },
            },
            required: ["user_id"],
        },
    },
    {
        name: "delete_user_profile",
        description: `删除用户档案。
    
警告：此操作不可逆，将永久删除用户的所有数据。`,
        inputSchema: {
            type: "object",
            properties: {
                user_id: {
                    type: "string",
                    description: "用户ID",
                },
            },
            required: ["user_id"],
        },
    },
    {
        name: "list_user_profiles",
        description: `列出所有已创建的用户档案ID。
    
用于查看系统中存在哪些用户档案。`,
        inputSchema: {
            type: "object",
            properties: {},
        },
    },
    // ============ 前端集成工具 ============
    {
        name: "sync_from_frontend",
        description: `从前端localStorage同步用户数据到MCP服务器的会话存储。

🔑 核心特性：
- 会话存储：数据临时存储，用于AI对话期间访问
- 自动过期：会话数据1小时后自动清除
- 隔离性：每个会话使用独立的session_id
- 增量同步：支持只同步变化的数据

📦 适用场景：
1. AI对话开始时同步用户档案
2. 用户更新数据后增量同步
3. 多设备数据临时共享

⚠️ 重要说明：
- 前端localStorage是唯一真实数据源
- MCP服务器只做临时存储，不替代前端存储
- 会话结束后应调用clear_session_data清除数据`,
        inputSchema: {
            type: "object",
            properties: {
                user_id: {
                    type: "string",
                    description: "用户ID",
                },
                frontend_data: {
                    type: "object",
                    description: "前端localStorage的用户数据（JSON对象）",
                },
                sync_mode: {
                    type: "string",
                    enum: ["full", "incremental"],
                    description: "同步模式：full=全量同步, incremental=增量同步（默认：full）",
                },
                session_id: {
                    type: "string",
                    description: "会话ID（可选，不提供则自动生成）",
                },
            },
            required: ["user_id", "frontend_data"],
        },
    },
    {
        name: "export_user_data",
        description: `导出用户的所有数据，用于备份或跨设备迁移。

📤 导出内容：
- 持久化存储的数据（如果存在）
- 会话存储的数据（如果存在）
- 导出元数据（时间戳、版本号等）

🎯 使用场景：
1. 用户数据备份
2. 跨设备数据迁移
3. 数据分析导出

💾 支持格式：
- json：JSON格式（默认）
- csv：CSV格式（未来支持）`,
        inputSchema: {
            type: "object",
            properties: {
                user_id: {
                    type: "string",
                    description: "用户ID",
                },
                format: {
                    type: "string",
                    enum: ["json", "csv"],
                    description: "导出格式（默认：json）",
                },
                include_history: {
                    type: "boolean",
                    description: "是否包含历史记录（默认：true）",
                },
            },
            required: ["user_id"],
        },
    },
    {
        name: "clear_session_data",
        description: `清除MCP服务器上的会话数据，保护用户隐私。

🗑️ 清除策略：
- 指定session_id：只清除该会话
- 不指定session_id：清除该用户的所有会话

⏰ 自动清理：
- 会话数据会在1小时后自动过期清除
- 建议在对话结束时主动调用此工具

🔒 隐私保护：
- 前端数据不受影响（localStorage是主存储）
- 只清除MCP服务器的临时会话数据
- 透明性：返回已清除的会话列表

📝 最佳实践：
在对话结束时调用：
onDialogEnd(() => {
  clearSessionData(userId, sessionId);
});`,
        inputSchema: {
            type: "object",
            properties: {
                user_id: {
                    type: "string",
                    description: "用户ID",
                },
                session_id: {
                    type: "string",
                    description: "会话ID（可选，不提供则清除所有会话）",
                },
            },
            required: ["user_id"],
        },
    },
];
// 注册工具处理器
server.setRequestHandler(ListToolsRequestSchema, async () => {
    return { tools };
});
server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    try {
        switch (name) {
            case "create_user_profile": {
                const schema = z.object({
                    user_id: z.string(),
                    basic_info: z.object({}).passthrough().optional(),
                    nutrition_profile: z.object({}).passthrough().optional(),
                    fitness_config: z.object({}).passthrough().optional(),
                    fitness_goals: z.object({}).passthrough().optional(),
                    strength_levels: z.object({}).passthrough().optional(),
                });
                const validated = schema.parse(args);
                const profile = manager.createProfile(validated.user_id, validated);
                return {
                    content: [
                        {
                            type: "text",
                            text: JSON.stringify({
                                success: true,
                                message: "用户档案创建成功",
                                profile: profile,
                            }, null, 2),
                        },
                    ],
                };
            }
            case "get_user_profile": {
                const schema = z.object({
                    user_id: z.string(),
                });
                const validated = schema.parse(args);
                const profile = await manager.getProfile(validated.user_id); // ✅ 添加await
                return {
                    content: [
                        {
                            type: "text",
                            text: JSON.stringify({
                                success: true,
                                profile: profile,
                            }, null, 2),
                        },
                    ],
                };
            }
            case "update_user_profile": {
                const schema = z.object({
                    user_id: z.string(),
                    basic_info: z.object({}).passthrough().optional(),
                    nutrition_profile: z.object({}).passthrough().optional(),
                    fitness_config: z.object({}).passthrough().optional(),
                    fitness_goals: z.object({}).passthrough().optional(),
                    strength_levels: z.object({}).passthrough().optional(),
                });
                const validated = schema.parse(args);
                const profile = await manager.updateProfile(validated.user_id, validated); // ✅ 添加await
                return {
                    content: [
                        {
                            type: "text",
                            text: JSON.stringify({
                                success: true,
                                message: "用户档案更新成功",
                                profile: profile,
                            }, null, 2),
                        },
                    ],
                };
            }
            case "delete_user_profile": {
                const schema = z.object({
                    user_id: z.string(),
                });
                const validated = schema.parse(args);
                manager.deleteProfile(validated.user_id);
                return {
                    content: [
                        {
                            type: "text",
                            text: JSON.stringify({
                                success: true,
                                message: `用户档案 ${validated.user_id} 已删除`,
                            }, null, 2),
                        },
                    ],
                };
            }
            case "ping": {
                return {
                    content: [
                        {
                            type: "text",
                            text: JSON.stringify({
                                success: true,
                                message: "pong",
                                timestamp: new Date().toISOString(),
                            }, null, 2),
                        },
                    ],
                };
            }
            case "list_user_profiles": {
                const userIds = manager.listProfiles();
                return {
                    content: [
                        {
                            type: "text",
                            text: JSON.stringify({
                                success: true,
                                count: userIds.length,
                                user_ids: userIds,
                            }, null, 2),
                        },
                    ],
                };
            }
            // ============ 前端集成工具 ============
            case "sync_from_frontend": {
                const schema = z.object({
                    user_id: z.string(),
                    frontend_data: z.any(),
                    sync_mode: z.enum(["full", "incremental"]).optional(),
                    session_id: z.string().optional(),
                });
                const validated = schema.parse(args);
                const result = manager.syncFromFrontend(validated.user_id, validated.frontend_data, validated.sync_mode, validated.session_id);
                return {
                    content: [
                        {
                            type: "text",
                            text: JSON.stringify(result, null, 2),
                        },
                    ],
                };
            }
            case "export_user_data": {
                const schema = z.object({
                    user_id: z.string(),
                    format: z.enum(["json", "csv"]).optional(),
                    include_history: z.boolean().optional(),
                });
                const validated = schema.parse(args);
                const result = manager.exportUserData(validated.user_id, validated.format, validated.include_history);
                return {
                    content: [
                        {
                            type: "text",
                            text: JSON.stringify(result, null, 2),
                        },
                    ],
                };
            }
            case "clear_session_data": {
                const schema = z.object({
                    user_id: z.string(),
                    session_id: z.string().optional(),
                });
                const validated = schema.parse(args);
                const result = manager.clearSessionData(validated.user_id, validated.session_id);
                return {
                    content: [
                        {
                            type: "text",
                            text: JSON.stringify(result, null, 2),
                        },
                    ],
                };
            }
            default:
                throw new Error(`未知工具: ${name}`);
        }
    }
    catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        return {
            content: [
                {
                    type: "text",
                    text: JSON.stringify({
                        success: false,
                        error: errorMessage,
                    }, null, 2),
                },
            ],
            isError: true,
        };
    }
});
// 启动服务器
async function main() {
    console.error("🚀 Starting User Profile MCP Server v2.1 (stdio)...");
    console.error("✅ User Profile MCP Server running on stdio");
    console.error("🆕 Enhanced with nutrition guide fields");
    console.error("📍 Regions: 华北、东北、华东、华南、西南、西北、华中");
    console.error("👥 Populations: 孕妇、乳母、婴幼儿、儿童青少年、老年人、素食人群");
    console.error("");
    console.error("🔄 Frontend Integration Tools:");
    console.error("   - sync_from_frontend: 从前端同步数据（会话存储）");
    console.error("   - export_user_data: 导出用户数据");
    console.error("   - clear_session_data: 清除会话数据");
    console.error("   ⏰ 会话数据自动清理：1小时TTL");
    const transport = new StdioServerTransport();
    await server.connect(transport);
}
main().catch((error) => {
    console.error("❌ Fatal error:", error);
    process.exit(1);
});
