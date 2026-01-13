/**
 * 简化的GraphRAG客户端
 *
 * 直接调用DAML-RAG API，避免复杂的模块引用
 *
 * 版本: v1.0.0
 * 创建: 2025-11-12
 * 作者: 薛小川
 */
export type QueryType = 'semantic_search' | 'graph_query' | 'hybrid' | 'biomechanics' | 'nutrition_analysis' | 'health_assessment';
export type Domain = 'fitness_exercises' | 'muscle_anatomy' | 'nutrition_guidelines' | 'injury_rehabilitation' | 'health_assessment';
export interface QueryFilters {
    muscle_groups?: string[];
    equipment?: string[];
    difficulty?: 'beginner' | 'intermediate' | 'advanced';
    injury_types?: string[];
    dietary_restrictions?: string[];
    allergies?: string[];
    age_group?: string;
    chronic_conditions?: string[];
    medications?: string[];
    region?: string;
    evidence_level?: 'A' | 'B' | 'C';
    reliability_score_min?: number;
}
export interface GraphRAGResult {
    id: string;
    type: 'exercise' | 'muscle' | 'food' | 'nutrient';
    name: string;
    description?: string;
    confidence_score: number;
    evidence_level: 'A' | 'B' | 'C';
    properties?: Record<string, any>;
}
export interface EvidenceSource {
    type: 'muscle_anatomy' | 'exercise_science' | 'nutrition_guide' | 'clinical_research';
    source: string;
    reliability_score: number;
    url?: string;
}
export interface GraphRAGResponse {
    success: boolean;
    results: GraphRAGResult[];
    reasoning?: string;
    evidence_sources: EvidenceSource[];
    cache_hit: boolean;
    query_time_ms: number;
    muscle_coverage_rate?: number;
    mapping_success_rate?: number;
}
export declare class SimpleGraphRAGClient {
    private endpoint;
    private timeout;
    constructor(endpoint?: string, timeout?: number);
    query(request: {
        query_text: string;
        query_type?: QueryType;
        domain?: Domain;
        filters?: QueryFilters;
        top_k?: number;
        return_reason?: boolean;
    }): Promise<GraphRAGResponse>;
}
export interface NutritionAnalysisRequest {
    user_profile: {
        age?: number;
        gender?: 'male' | 'female';
        weight?: number;
        height?: number;
        activity_level?: 'sedentary' | 'light' | 'moderate' | 'active' | 'very_active';
        dietary_restrictions?: string[];
        allergies?: string[];
        chronic_conditions?: string[];
        medications?: string[];
        region?: string;
    };
    query_text: string;
}
export interface NutritionAnalysisResponse {
    safe: boolean;
    recommendations: string[];
    warnings: string[];
    alternatives: string[];
    evidence_sources: EvidenceSource[];
}
export interface HealthAssessmentRequest {
    user_profile: {
        age?: number;
        gender?: 'male' | 'female';
        weight?: number;
        height?: number;
        chronic_conditions?: string[];
        medications?: string[];
        injury_history?: string[];
    };
    query_text: string;
}
export interface HealthAssessmentResponse {
    risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
    recommendations: string[];
    contraindications: string[];
    evidence_sources: EvidenceSource[];
}
export declare class UserProfileGraphRAGService extends SimpleGraphRAGClient {
    /**
     * 营养安全性分析
     */
    analyzeNutritionSafety(request: NutritionAnalysisRequest): Promise<NutritionAnalysisResponse>;
    /**
     * 健康状况评估
     */
    assessHealth(request: HealthAssessmentRequest): Promise<HealthAssessmentResponse>;
    private getAgeGroup;
}
export declare function createUserProfileGraphRAGService(endpoint?: string): UserProfileGraphRAGService;
