"""
社区检索器 - 提供社区级别的上下文信息
"""

import json
import os
from typing import List, Dict, Optional


class CommunityRetriever:
    """社区检索器"""
    
    def __init__(self, summaries_path: str = "/app/data/community_summaries.json"):
        self.summaries_path = summaries_path
        self.communities = []
        self._load_summaries()
        
    def _load_summaries(self):
        """加载社区摘要"""
        if os.path.exists(self.summaries_path):
            with open(self.summaries_path, 'r', encoding='utf-8') as f:
                self.communities = json.load(f)
            print(f"已加载 {len(self.communities)} 个社区摘要")
        else:
            print(f"警告: 社区摘要文件不存在: {self.summaries_path}")
            
    def get_community_context(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        根据查询返回相关社区摘要
        
        Args:
            query: 用户查询
            top_k: 返回前k个相关社区
            
        Returns:
            相关社区摘要列表
        """
        if not self.communities:
            return []
        
        # 肌肉名映射（模糊匹配）
        muscle_map = {
            "胸": ["胸部", "上胸", "中胸与下胸"],
            "背": ["背阔肌", "斜方肌", "下背部"],
            "肩": ["三角肌前束", "三角肌中束", "三角肌后束", "肩部"],
            "腿": ["股四头肌", "腘绳肌", "臀部", "小腿"],
            "臀": ["臀部", "臀中肌"],
            "腹": ["腹直肌", "腹斜肌", "上腹肌", "下腹部"],
            "二头": ["肱二头肌", "肱二头肌长头", "肱二头肌短头"],
            "三头": ["肱三头肌", "三头肌长头", "肱三头肌外侧头"],
            "前臂": ["前臂肌群", "腕伸肌群"]
        }
        
        # 简单关键词匹配
        scored_communities = []
        for comm in self.communities:
            score = 0
            
            # 匹配肌肉名（模糊匹配）
            for keyword, muscles in muscle_map.items():
                if keyword in query:
                    for muscle in comm.get("primary_muscles", []):
                        if muscle in muscles:
                            score += 5
            
            # 直接匹配肌肉名
            for muscle in comm.get("primary_muscles", []):
                if muscle in query:
                    score += 5
            
            # 匹配动作名
            for exercise in comm.get("sample_exercises", []):
                if exercise in query:
                    score += 2
            
            # 匹配器械
            for equipment in comm.get("common_equipment", []):
                if equipment in query:
                    score += 1
            
            # 匹配force类型
            force_dist = comm.get("force_distribution", {})
            if "推" in query and "推力" in force_dist:
                score += 3
            if "拉" in query and "拉力" in force_dist:
                score += 3
            if "保持" in query or "静态" in query:
                if "保持" in force_dist:
                    score += 3
            
            # 匹配mechanic类型
            mechanic_dist = comm.get("mechanic_distribution", {})
            if "复合" in query and "复合动作" in mechanic_dist:
                score += 2
            if "孤立" in query or "单关节" in query:
                if "单关节动作" in mechanic_dist:
                    score += 2
            
            if score > 0:
                scored_communities.append((score, comm))
        
        # 排序并返回top_k
        scored_communities.sort(key=lambda x: -x[0])
        return [comm for _, comm in scored_communities[:top_k]]
    
    def get_community_by_id(self, community_id: int) -> Optional[Dict]:
        """根据社区ID获取摘要"""
        for comm in self.communities:
            if comm["community_id"] == community_id:
                return comm
        return None
    
    def format_context(self, communities: List[Dict]) -> str:
        """格式化社区上下文为文本"""
        if not communities:
            return ""
        
        context_parts = ["## 相关训练社区背景\n"]
        for comm in communities:
            context_parts.append(f"### {comm['name']}")
            context_parts.append(f"- 包含动作: {comm['exercise_count']}个")
            context_parts.append(f"- 主要肌肉: {', '.join(comm['primary_muscles'][:3])}")
            context_parts.append(f"- 常用器械: {', '.join(comm['common_equipment'])}")
            context_parts.append(f"- 特征: {comm['summary']}\n")
        
        return "\n".join(context_parts)


# 全局单例
_retriever_instance = None


def get_community_retriever() -> CommunityRetriever:
    """获取社区检索器单例"""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = CommunityRetriever()
    return _retriever_instance
