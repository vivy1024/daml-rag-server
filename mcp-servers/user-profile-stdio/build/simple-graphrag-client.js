/**
 * 简化的GraphRAG客户端
 *
 * 直接调用DAML-RAG API，避免复杂的模块引用
 *
 * 版本: v1.0.0
 * 创建: 2025-11-12
 * 作者: 薛小川
 */
// =============================================================================
// 简化的GraphRAG客户端
// =============================================================================
export class SimpleGraphRAGClient {
    endpoint;
    timeout;
    constructor(endpoint = 'http://localhost:8001', timeout = 10000) {
        this.endpoint = endpoint;
        this.timeout = timeout;
    }
    async query(request) {
        const startTime = Date.now();
        try {
            // 构建请求
            const requestBody = {
                query_type: request.query_type || 'hybrid',
                domain: request.domain || 'fitness_exercises',
                query_text: request.query_text,
                filters: request.filters || {},
                top_k: request.top_k || 10,
                return_reason: request.return_reason !== false
            };
            console.log('🔍 GraphRAG查询:', requestBody);
            // 发送HTTP请求
            const response = await fetch(`${this.endpoint}/api/graphrag/query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody),
                signal: AbortSignal.timeout(this.timeout)
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const data = await response.json();
            // 转换响应格式
            const result = {
                success: data.success || true,
                results: data.results || [],
                reasoning: data.reasoning,
                evidence_sources: data.evidence_sources || [],
                cache_hit: data.cache_hit || false,
                query_time_ms: Date.now() - startTime,
                muscle_coverage_rate: data.muscle_coverage_rate,
                mapping_success_rate: data.mapping_success_rate
            };
            console.log(`✅ GraphRAG查询成功: ${result.results.length}个结果, 耗时${result.query_time_ms}ms`);
            return result;
        }
        catch (error) {
            console.error('❌ GraphRAG查询失败:', error);
            return {
                success: false,
                results: [],
                reasoning: `查询失败: ${error instanceof Error ? error.message : '未知错误'}`,
                evidence_sources: [],
                cache_hit: false,
                query_time_ms: Date.now() - startTime
            };
        }
    }
}
// =============================================================================
// 用户档案专用GraphRAG服务
// =============================================================================
export class UserProfileGraphRAGService extends SimpleGraphRAGClient {
    /**
     * 营养安全性分析
     */
    async analyzeNutritionSafety(request) {
        console.log('🍽️ 执行营养安全性分析...');
        const graphragResponse = await this.query({
            query_text: request.query_text,
            query_type: 'nutrition_analysis',
            domain: 'nutrition_guidelines',
            filters: {
                dietary_restrictions: request.user_profile.dietary_restrictions,
                allergies: request.user_profile.allergies,
                chronic_conditions: request.user_profile.chronic_conditions,
                medications: request.user_profile.medications,
                region: request.user_profile.region,
                age_group: this.getAgeGroup(request.user_profile.age),
                evidence_level: 'B',
                reliability_score_min: 0.7
            },
            top_k: 8,
            return_reason: true
        });
        // 分析安全性
        const warnings = [];
        const recommendations = [];
        const alternatives = [];
        // 基于结果分析安全性
        if (graphragResponse.success) {
            for (const result of graphragResponse.results) {
                if (result.type === 'food' || result.type === 'nutrient') {
                    if (result.confidence_score < 0.7) {
                        warnings.push(`${result.name}: 可能有相互作用，建议咨询医生`);
                    }
                    else {
                        recommendations.push(`${result.name}: 相对安全，适量食用`);
                    }
                }
            }
        }
        // 生成替代建议
        if (warnings.length > 0) {
            alternatives.push('建议选择经过科学验证的营养补充方案');
            alternatives.push('考虑咨询专业营养师制定个性化方案');
        }
        return {
            safe: warnings.length === 0,
            recommendations,
            warnings,
            alternatives,
            evidence_sources: graphragResponse.evidence_sources
        };
    }
    /**
     * 健康状况评估
     */
    async assessHealth(request) {
        console.log('🏥 执行健康状况评估...');
        // 确定风险等级
        let riskLevel = 'LOW';
        if (request.user_profile.chronic_conditions && request.user_profile.chronic_conditions.length > 0) {
            riskLevel = 'MEDIUM';
        }
        if (request.user_profile.medications && request.user_profile.medications.length > 2) {
            riskLevel = 'HIGH';
        }
        const graphragResponse = await this.query({
            query_text: request.query_text,
            query_type: 'health_assessment',
            domain: 'health_assessment',
            filters: {
                chronic_conditions: request.user_profile.chronic_conditions,
                evidence_level: 'A',
                reliability_score_min: 0.8
            },
            top_k: 6,
            return_reason: true
        });
        // 生成建议和禁忌
        const recommendations = [];
        const contraindications = [];
        if (graphragResponse.success) {
            for (const result of graphragResponse.results) {
                if (result.confidence_score > 0.8) {
                    recommendations.push(result.description || result.name);
                }
            }
        }
        // 基于风险等级添加通用建议
        if (riskLevel === 'HIGH') {
            contraindications.push('高强度运动前必须咨询医生');
            contraindications.push('避免突然改变运动强度');
            recommendations.push('建议从低强度运动开始，逐步适应');
        }
        return {
            risk_level: riskLevel,
            recommendations,
            contraindications,
            evidence_sources: graphragResponse.evidence_sources
        };
    }
    getAgeGroup(age) {
        if (!age)
            return 'adult';
        if (age < 18)
            return 'teenager';
        if (age < 30)
            return 'young_adult';
        if (age < 50)
            return 'adult';
        if (age < 65)
            return 'middle_aged';
        return 'senior';
    }
}
// =============================================================================
// 工厂函数
// =============================================================================
export function createUserProfileGraphRAGService(endpoint) {
    return new UserProfileGraphRAGService(endpoint);
}
