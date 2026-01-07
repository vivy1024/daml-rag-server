"""
Exercise节点数据补充器

功能：
1. 补充运动链类型 (kinetic_chain_type)
2. 数据质量检查 (检测description_zh和correct_steps_zh重复)
3. 补充技术检查点 (technique_checkpoints)
4. 补充关节活动度要求 (rom_requirements)

作者：薛小川
日期：2025-12-15
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from neo4j import AsyncDriver

try:
    from ollama import AsyncClient
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    AsyncClient = None

from .models import SupplementResult

logger = logging.getLogger(__name__)


class ExerciseSupplementer:
    """Exercise节点补充器"""
    
    def __init__(self, neo4j_driver: AsyncDriver):
        """
        初始化补充器
        
        Args:
            neo4j_driver: Neo4j异步驱动
        """
        self.driver = neo4j_driver
        self.ollama_client = None
        
        # 运动链分类规则
        self.kinetic_chain_rules = self._load_kinetic_chain_rules()
        
        # 关键动作的技术检查点模板
        self.technique_templates = self._load_technique_templates()
        
        # 关节活动度要求
        self.rom_requirements = self._load_rom_requirements()
    
    def _load_kinetic_chain_rules(self) -> Dict[str, List[str]]:
        """加载运动链分类规则"""
        return {
            # 闭链动作（Closed Chain）- 远端固定
            "closed_chain": [
                "深蹲", "硬拉", "卧推", "引体向上", "俯卧撑",
                "箭步蹲", "弓步", "登山", "爬山", "蹬腿",
                "倒蹬", "腿举", "臀桥", "臀冲", "划船"
            ],
            # 开链动作（Open Chain）- 远端自由
            "open_chain": [
                "弯举", "飞鸟", "侧平举", "前平举", "后束",
                "腿屈伸", "腿弯举", "小腿提踵", "卷腹", "仰卧起坐",
                "下拉", "推举", "臂屈伸", "腕弯举"
            ]
        }
    
    def _load_technique_templates(self) -> Dict[str, List[str]]:
        """加载关键动作的技术检查点模板"""
        return {
            "杠铃深蹲": [
                "起始：双脚与肩同宽，脚尖略外展，杠铃放在斜方肌上部",
                "下蹲：膝盖与脚尖方向一致，大腿至少平行地面，保持核心稳定",
                "上升：均匀发力，保持背部平直，避免膝盖内扣"
            ],
            "杠铃硬拉": [
                "起始：杠铃贴近小腿，肩膀在杠铃正上方，背部平直",
                "拉起：保持背部平直，髋关节和膝关节同时伸展，杠铃贴近身体",
                "锁定：站直时肩膀后缩，髋关节完全伸展，避免过度后仰"
            ],
            "杠铃卧推": [
                "起始：肩胛骨后缩下沉，双脚踩实地面，握距略宽于肩",
                "下降：肘关节约45度角，杠铃触胸位置在乳头附近",
                "推起：保持肩胛骨稳定，均匀发力，避免肩膀前伸"
            ],
            "引体向上": [
                "起始：双手握杠略宽于肩，身体悬垂，肩胛骨下沉",
                "拉起：肩胛骨后缩，肘关节向下拉，下巴超过杠铃",
                "下降：控制下降速度，保持肩胛骨稳定，避免完全放松"
            ],
            "哑铃弯举": [
                "起始：站立，双手持哑铃自然下垂，肘关节贴近身体",
                "弯举：肘关节固定，屈肘将哑铃举至肩部，避免借力摆动",
                "下降：控制下降速度，保持肌肉张力，避免完全伸直"
            ]
        }
    
    def _load_rom_requirements(self) -> Dict[str, Dict[str, int]]:
        """加载关节活动度要求"""
        return {
            "杠铃深蹲": {
                "hip_flexion": 90,
                "knee_flexion": 90,
                "ankle_dorsiflexion": 15
            },
            "杠铃硬拉": {
                "hip_flexion": 90,
                "knee_flexion": 30
            },
            "杠铃卧推": {
                "shoulder_horizontal_abduction": 90,
                "elbow_flexion": 90
            },
            "引体向上": {
                "shoulder_flexion": 180,
                "elbow_flexion": 140
            },
            "哑铃弯举": {
                "elbow_flexion": 140
            }
        }
    
    async def supplement(self, use_ollama: bool = False, batch_size: int = 100) -> SupplementResult:
        """
        执行完整的Exercise节点补充流程
        
        Args:
            use_ollama: 是否使用Ollama生成技术检查点
            batch_size: Ollama批量生成的批次大小
        
        Returns:
            SupplementResult: 补充结果
        """
        start_time = time.time()
        logger.info("开始Exercise节点数据补充")
        
        try:
            with self.driver.session() as session:
                # 0. 数据质量检查
                logger.info("步骤0：数据质量检查")
                quality_report = self._check_data_quality(session)
                
                # 1. 补充运动链类型
                logger.info("步骤1：补充运动链类型")
                self._supplement_kinetic_chain_type(session)
                
                # 2. 补充技术检查点（关键动作）
                logger.info("步骤2：补充技术检查点（关键动作）")
                self._supplement_technique_checkpoints_manual(session)
                
                # 2.5. 使用Ollama生成技术检查点（可选）
                if use_ollama:
                    logger.info("步骤2.5：使用Ollama生成技术检查点")
                    await self._supplement_technique_checkpoints_with_llm(session, batch_size)
                
                # 3. 补充关节活动度要求
                logger.info("步骤3：补充关节活动度要求")
                self._supplement_rom_requirements(session)
                
                # 统计结果
                total_nodes = self._count_exercise_nodes(session)
                updated_nodes = self._count_updated_nodes(session)
                
                execution_time = time.time() - start_time
                
                logger.info(f"Exercise节点数据补充完成")
                logger.info(f"总节点数: {total_nodes}")
                logger.info(f"已更新节点数: {updated_nodes}")
                logger.info(f"执行时间: {execution_time:.2f}秒")
                
                return SupplementResult(
                    total_nodes=total_nodes,
                    updated_nodes=updated_nodes,
                    errors=[],
                    quality_report=quality_report,
                    execution_time=execution_time
                )
        
        except Exception as e:
            logger.error(f"Exercise节点补充失败: {e}", exc_info=True)
            execution_time = time.time() - start_time
            return SupplementResult(
                total_nodes=0,
                updated_nodes=0,
                errors=[{"stage": "exercise_supplement", "error": str(e)}],
                execution_time=execution_time
            )
    
    def _check_data_quality(self, session) -> Dict[str, Any]:
        """
        检查数据质量问题
        
        Args:
            session: Neo4j会话
            
        Returns:
            Dict: 数据质量报告
        """
        logger.info("检查description_zh和correct_steps_zh重复情况...")
        
        # 检查重复
        query = """
        MATCH (e:Exercise)
        WHERE e.description_zh = e.correct_steps_zh
        RETURN count(e) as duplicate_count
        """
        result = session.run(query)
        record = result.single()
        duplicate_count = record["duplicate_count"]
        
        # 统计总数
        total_query = "MATCH (e:Exercise) RETURN count(e) as total"
        total_result = session.run(total_query)
        total_record = total_result.single()
        total_count = total_record["total"]
        
        duplicate_percentage = (duplicate_count / total_count * 100) if total_count > 0 else 0
        
        quality_report = {
            "duplicate_description_steps": duplicate_count,
            "total_exercises": total_count,
            "duplicate_percentage": round(duplicate_percentage, 2),
            "check_time": datetime.now().isoformat()
        }
        
        logger.info(f"数据质量检查完成")
        logger.info(f"  总动作数: {total_count}")
        logger.info(f"  重复数: {duplicate_count}")
        logger.info(f"  重复比例: {duplicate_percentage:.2f}%")
        
        # 标记需要人工审核的动作
        if duplicate_count > 0:
            logger.info(f"标记 {duplicate_count} 个动作为需要人工审核...")
            mark_query = """
            MATCH (e:Exercise)
            WHERE e.description_zh = e.correct_steps_zh
            SET e.needs_manual_review = true,
                e.review_reason = 'description和correct_steps重复'
            RETURN count(e) as marked_count
            """
            mark_result = session.run(mark_query)
            mark_record = mark_result.single()
            logger.info(f"已标记 {mark_record['marked_count']} 个动作")
        
        return quality_report
    
    def _supplement_kinetic_chain_type(self, session):
        """
        补充运动链类型
        
        Args:
            session: Neo4j会话
        """
        logger.info("开始补充运动链类型...")
        
        # 闭链动作
        closed_chain_keywords = self.kinetic_chain_rules["closed_chain"]
        total_closed = 0
        for keyword in closed_chain_keywords:
            query = """
            MATCH (e:Exercise)
            WHERE e.name_zh CONTAINS $keyword
            SET e.kinetic_chain_type = 'closed_chain'
            RETURN count(e) as updated_count
            """
            result = session.run(query, {"keyword": keyword})
            record = result.single()
            total_closed += record["updated_count"]
        
        # 开链动作
        open_chain_keywords = self.kinetic_chain_rules["open_chain"]
        total_open = 0
        for keyword in open_chain_keywords:
            query = """
            MATCH (e:Exercise)
            WHERE e.name_zh CONTAINS $keyword
            SET e.kinetic_chain_type = 'open_chain'
            RETURN count(e) as updated_count
            """
            result = session.run(query, {"keyword": keyword})
            record = result.single()
            total_open += record["updated_count"]
        
        # 混合动作（未分类的）
        query = """
        MATCH (e:Exercise)
        WHERE e.kinetic_chain_type IS NULL
        SET e.kinetic_chain_type = 'mixed'
        RETURN count(e) as updated_count
        """
        result = session.run(query)
        record = result.single()
        total_mixed = record["updated_count"]
        
        logger.info(f"运动链类型补充完成")
        logger.info(f"  闭链动作: {total_closed} 个")
        logger.info(f"  开链动作: {total_open} 个")
        logger.info(f"  混合动作: {total_mixed} 个")
    
    def _supplement_technique_checkpoints_manual(self, session):
        """
        为关键动作手动添加技术检查点
        
        Args:
            session: Neo4j会话
        """
        logger.info("为关键动作添加技术检查点...")
        
        updated_count = 0
        for exercise_name, checkpoints in self.technique_templates.items():
            # 验证JSON格式
            checkpoints_json = json.dumps(checkpoints, ensure_ascii=False)
            
            query = """
            MATCH (e:Exercise)
            WHERE e.name_zh = $name
            SET e.technique_checkpoints = $checkpoints,
                e.checkpoints_source = 'manual_template',
                e.checkpoints_updated_at = datetime()
            RETURN count(e) as count
            """
            result = session.run(query, {
                "name": exercise_name,
                "checkpoints": checkpoints_json
            })
            record = result.single()
            updated_count += record["count"]
        
        logger.info(f"关键动作技术检查点补充完成: {updated_count} 个")
    
    async def _supplement_technique_checkpoints_with_llm(self, session, batch_size: int = 100):
        """
        使用本地Ollama Qwen3 8B生成技术检查点
        
        Args:
            session: Neo4j会话
            batch_size: 批量生成的批次大小
        """
        logger.info(f"使用Ollama生成技术检查点（批次大小: {batch_size}）...")
        
        # 初始化Ollama客户端
        if self.ollama_client is None:
            # Docker容器内连接到宿主机Ollama
            ollama_host = "http://host.docker.internal:11434"
            self.ollama_client = AsyncClient(host=ollama_host)
            logger.info(f"  连接到Ollama: {ollama_host}")
        
        # 1. 查询需要生成technique_checkpoints的动作
        query = """
        MATCH (e:Exercise)
        WHERE e.technique_checkpoints IS NULL
          AND e.description_zh IS NOT NULL
        RETURN e.exercise_id as id, 
               e.name_zh as name, 
               e.description_zh as description,
               e.force as force,
               e.mechanic as mechanic,
               e.equipment_zh as equipment
        LIMIT $batch_size
        """
        
        result = session.run(query, {"batch_size": batch_size})
        exercises = [record.data() for record in result]
        
        if not exercises:
            logger.info("  没有需要生成技术检查点的动作")
            return
        
        logger.info(f"  找到 {len(exercises)} 个需要生成技术检查点的动作")
        
        # 2. 批量生成
        success_count = 0
        failed_count = 0
        
        for i, exercise in enumerate(exercises, 1):
            try:
                # 构建prompt
                prompt = self._build_checkpoint_prompt(exercise)
                
                # 调用Ollama生成
                response = await self.ollama_client.generate(
                    model='qwen3:8b',
                    prompt=prompt,
                    options={'temperature': 0.3}
                )
                
                # 解析响应
                checkpoints_text = response['response'].strip()
                
                # 尝试解析JSON
                try:
                    checkpoints = json.loads(checkpoints_text)
                except json.JSONDecodeError:
                    # 尝试提取JSON部分
                    import re
                    json_match = re.search(r'\[.*\]', checkpoints_text, re.DOTALL)
                    if json_match:
                        checkpoints = json.loads(json_match.group())
                    else:
                        raise ValueError("无法解析JSON")
                
                # 验证checkpoints是列表且不为空
                if not isinstance(checkpoints, list) or len(checkpoints) == 0:
                    raise ValueError("检查点格式不正确")
                
                # 3. 更新到Neo4j
                update_query = """
                MATCH (e:Exercise {exercise_id: $id})
                SET e.technique_checkpoints = $checkpoints,
                    e.checkpoints_source = 'ollama_qwen3_8b',
                    e.checkpoints_updated_at = datetime()
                RETURN e.name_zh as name
                """
                session.run(update_query, {
                    "id": exercise['id'],
                    "checkpoints": json.dumps(checkpoints, ensure_ascii=False)
                })
                
                success_count += 1
                if i % 10 == 0:
                    logger.info(f"  进度: {i}/{len(exercises)} ({success_count} 成功, {failed_count} 失败)")
                
            except Exception as e:
                failed_count += 1
                logger.warning(f"  为动作 {exercise['name']} 生成检查点失败: {e}")
                
                # 失败时使用通用模板
                fallback_checkpoints = [
                    "起始姿势：参考动作描述，保持正确的身体姿态",
                    "动作过程：保持控制和稳定，避免借力和代偿",
                    "结束姿势：完成完整动作幅度，保持肌肉张力"
                ]
                
                fallback_query = """
                MATCH (e:Exercise {exercise_id: $id})
                SET e.technique_checkpoints = $checkpoints,
                    e.checkpoints_source = 'fallback_template',
                    e.checkpoints_updated_at = datetime()
                """
                session.run(fallback_query, {
                    "id": exercise['id'],
                    "checkpoints": json.dumps(fallback_checkpoints, ensure_ascii=False)
                })
        
        logger.info(f"Ollama生成完成: {success_count} 成功, {failed_count} 失败")
    
    def _build_checkpoint_prompt(self, exercise: Dict[str, Any]) -> str:
        """
        构建生成技术检查点的prompt
        
        Args:
            exercise: 动作信息
            
        Returns:
            str: prompt文本
        """
        prompt = f"""你是一位专业的健身教练。请基于以下动作信息，生成3-5个关键的技术检查点。

动作名称：{exercise['name']}
动作描述：{exercise['description']}
力量类型：{exercise.get('force', '未知')}
力学特性：{exercise.get('mechanic', '未知')}
所需器械：{exercise.get('equipment', '未知')}

要求：
1. 技术检查点应该简洁、专业、可操作
2. 包含起始姿势、动作过程、结束姿势的关键要点
3. 强调安全性和正确发力
4. 以JSON数组格式输出，例如：["起始：...", "动作：...", "结束：..."]

请直接输出JSON数组，不要其他解释：
"""
        return prompt
    
    def _supplement_rom_requirements(self, session):
        """
        补充关节活动度要求
        
        Args:
            session: Neo4j会话
        """
        logger.info("补充关节活动度要求...")
        
        updated_count = 0
        for exercise_name, rom in self.rom_requirements.items():
            # 验证JSON格式和数值范围
            for joint, angle in rom.items():
                if not (0 <= angle <= 180):
                    logger.warning(f"  {exercise_name} 的 {joint} 角度 {angle} 超出范围")
            
            rom_json = json.dumps(rom, ensure_ascii=False)
            
            query = """
            MATCH (e:Exercise)
            WHERE e.name_zh = $name
            SET e.rom_requirements = $rom,
                e.rom_updated_at = datetime()
            RETURN count(e) as count
            """
            result = session.run(query, {
                "name": exercise_name,
                "rom": rom_json
            })
            record = result.single()
            updated_count += record["count"]
        
        logger.info(f"关节活动度要求补充完成: {updated_count} 个")
    
    def _count_exercise_nodes(self, session) -> int:
        """统计Exercise节点总数"""
        query = "MATCH (e:Exercise) RETURN count(e) as total"
        result = session.run(query)
        record = result.single()
        return record["total"]
    
    def _count_updated_nodes(self, session) -> int:
        """统计已更新的节点数"""
        query = """
        MATCH (e:Exercise)
        WHERE e.kinetic_chain_type IS NOT NULL
        RETURN count(e) as updated
        """
        result = session.run(query)
        record = result.single()
        return record["updated"]
