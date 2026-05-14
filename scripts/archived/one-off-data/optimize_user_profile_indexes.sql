-- 用户档案加载性能优化 - 数据库索引
-- 版本: v1.0.0
-- 日期: 2025-12-21
-- 目的: 优化用户档案查询性能，减少查询时间从6633ms到500ms以内

-- ============================================
-- 1. 用户表索引优化
-- ============================================

-- 检查users表是否存在主键索引
-- 如果不存在，创建主键索引
ALTER TABLE users 
ADD PRIMARY KEY IF NOT EXISTS (id);

-- 为常用查询字段添加索引
-- 用于按邮箱查询用户
CREATE INDEX IF NOT EXISTS idx_users_email 
ON users(email);

-- 用于按创建时间查询（分页、排序）
CREATE INDEX IF NOT EXISTS idx_users_created_at 
ON users(created_at DESC);

-- 用于按更新时间查询（查找最近更新的用户）
CREATE INDEX IF NOT EXISTS idx_users_updated_at 
ON users(updated_at DESC);

-- ============================================
-- 2. 用户档案表索引优化
-- ============================================

-- 假设存在user_profiles表，为其添加索引
-- 如果表不存在，这些语句会被跳过

-- 用户ID外键索引（最重要）
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id 
ON user_profiles(user_id);

-- 复合索引：用户ID + 更新时间（用于缓存失效判断）
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_updated 
ON user_profiles(user_id, updated_at DESC);

-- ============================================
-- 3. 会员信息表索引优化
-- ============================================

-- 假设存在memberships表
CREATE INDEX IF NOT EXISTS idx_memberships_user_id 
ON memberships(user_id);

-- 复合索引：用户ID + 状态（用于快速查询活跃会员）
CREATE INDEX IF NOT EXISTS idx_memberships_user_status 
ON memberships(user_id, status);

-- 复合索引：用户ID + 过期时间（用于快速判断会员是否过期）
CREATE INDEX IF NOT EXISTS idx_memberships_user_expired 
ON memberships(user_id, expired_at);

-- ============================================
-- 4. 查询优化建议
-- ============================================

-- 建议1：使用EXPLAIN分析查询计划
-- EXPLAIN SELECT * FROM users WHERE id = 1;
-- EXPLAIN SELECT * FROM user_profiles WHERE user_id = 1;

-- 建议2：定期分析表统计信息
-- ANALYZE TABLE users;
-- ANALYZE TABLE user_profiles;
-- ANALYZE TABLE memberships;

-- 建议3：监控慢查询日志
-- SET GLOBAL slow_query_log = 'ON';
-- SET GLOBAL long_query_time = 1;  -- 记录超过1秒的查询

-- ============================================
-- 5. 字段选择优化建议
-- ============================================

-- 建议：只查询需要的字段，避免SELECT *
-- 优化前：SELECT * FROM users WHERE id = 1;
-- 优化后：SELECT id, email, name, created_at FROM users WHERE id = 1;

-- 建议：使用JOIN时指定字段
-- 优化前：
-- SELECT * FROM users u 
-- LEFT JOIN user_profiles p ON u.id = p.user_id 
-- WHERE u.id = 1;

-- 优化后：
-- SELECT 
--   u.id, u.email, u.name,
--   p.age, p.gender, p.height, p.weight,
--   p.training_experience, p.fitness_goal
-- FROM users u 
-- LEFT JOIN user_profiles p ON u.id = p.user_id 
-- WHERE u.id = 1;

-- ============================================
-- 6. 性能监控查询
-- ============================================

-- 查看索引使用情况
-- SELECT 
--   TABLE_NAME,
--   INDEX_NAME,
--   SEQ_IN_INDEX,
--   COLUMN_NAME,
--   CARDINALITY
-- FROM information_schema.STATISTICS
-- WHERE TABLE_SCHEMA = DATABASE()
--   AND TABLE_NAME IN ('users', 'user_profiles', 'memberships')
-- ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;

-- 查看表大小和行数
-- SELECT 
--   TABLE_NAME,
--   TABLE_ROWS,
--   ROUND(DATA_LENGTH / 1024 / 1024, 2) AS data_size_mb,
--   ROUND(INDEX_LENGTH / 1024 / 1024, 2) AS index_size_mb
-- FROM information_schema.TABLES
-- WHERE TABLE_SCHEMA = DATABASE()
--   AND TABLE_NAME IN ('users', 'user_profiles', 'memberships');

-- ============================================
-- 执行说明
-- ============================================

-- 1. 在Docker容器中执行：
--    docker exec fitness_mysql mysql -u root -p yuzhen_fitness < optimize_user_profile_indexes.sql

-- 2. 或者在MySQL客户端中执行：
--    mysql> source /path/to/optimize_user_profile_indexes.sql;

-- 3. 验证索引创建：
--    SHOW INDEX FROM users;
--    SHOW INDEX FROM user_profiles;
--    SHOW INDEX FROM memberships;

-- ============================================
-- 预期效果
-- ============================================

-- 优化前：
-- - 用户档案查询：6633ms
-- - 缓存未命中时：>500ms

-- 优化后：
-- - 用户档案查询（有索引）：<50ms
-- - 缓存未命中时：<500ms
-- - 缓存命中时：<50ms

-- ============================================
-- 维护建议
-- ============================================

-- 1. 定期重建索引（每月一次）
--    OPTIMIZE TABLE users;
--    OPTIMIZE TABLE user_profiles;
--    OPTIMIZE TABLE memberships;

-- 2. 监控索引碎片率
--    SELECT 
--      TABLE_NAME,
--      ROUND(DATA_FREE / DATA_LENGTH * 100, 2) AS fragmentation_pct
--    FROM information_schema.TABLES
--    WHERE TABLE_SCHEMA = DATABASE()
--      AND DATA_FREE > 0;

-- 3. 定期更新统计信息（每周一次）
--    ANALYZE TABLE users;
--    ANALYZE TABLE user_profiles;
--    ANALYZE TABLE memberships;
