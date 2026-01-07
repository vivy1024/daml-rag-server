"""
训练量标准导入器

功能：
1. 读取training-volume-landmarks.json
2. 匹配Muscle节点（通过name_zh）
3. 更新mev、mav、mrv、mv、optimal_frequency属性
4. 实现幂等性：检查属性是否已存在

作者：薛小川
日期：2025-12-19
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from neo4j import AsyncDriver

from .models import SupplementResult

logger = logging.getLogger(__name__)


class TrainingVolumeSupplementer:
    """训练量标准补充器"""
    
    def __init__(self, neo4j_driver: AsyncDriver, data_dir: str = "data/training_knowledge"):
        """
        初始化补充器
        
        Args:
            neo4j_driver: Neo4j异步驱动
            data_dir: 数据文件目录
        """
        self.driver = neo4j_driver
        self.data_dir = Path(data_dir)
        self.data_file = self.data_dir / "training-volume-landmarks.json"
        
        # 肌肉名称映射（英文 -> 中文）
        # 注意：这里的中文名称必须与Neo4j中的Muscle节点的name_zh字段完全匹配
        self.muscle_name_mapping = {
            "chest": "胸部",  # Neo4j中使用"胸部"而非"胸大肌"
            "back": "背阔肌",
            "front_delts": "前三角肌",
            "side_delts": "侧三角肌",  # Neo4j中使用"侧三角肌"而非"中三角肌"
            "rear_delts": "后束三角肌",  # Neo4j中使用"后束三角肌"而非"后三角肌"
            "biceps": "肱二头肌",
            "triceps": "肱三头肌",
            "quads": "股四头肌",
            "hamstrings": "腘绳肌",
            "glutes": "臀大肌",
            "calves": "腓肠肌",  # Neo4j中使用"腓肠肌"而非"小腿三头肌"
            "abs": "腹直肌"
        }
    
    async def supplement(self) -> SupplementResult:
        """
        执行训练量标准补充流程
        
        Returns:
            SupplementResult: 补充结果
        """
        start_time = time.time()
        logger.info("开始训练量标准补充")
        
        try:
            # 1. 读取数据文件
            logger.info(f"读取数据文件: {self.data_file}")
            volume_data = self._load_volume_data()
            
            if not volume_data:
                logger.error("训练量数据为空")
                return SupplementResult(
                    total_nodes=0,
                    updated_nodes=0,
                    errors=[{"stage": "load_data", "error": "训练量数据为空"}],
                    execution_time=time.time() - start_time
                )
            
            # 2. 更新Muscle节点
            async with self.driver.session() as session:
                # 统计总节点数
                total_nodes = await self._count_muscle_nodes(session)
                logger.info(f"找到 {total_nodes} 个Muscle节点")
                
                # 更新节点
                updated_count = 0
                skipped_count = 0
                errors = []
                
                for muscle_key, volume_info in volume_data.items():
                    try:
                        # 获取中文肌肉名称
                        muscle_name_zh = self.muscle_name_mapping.get(muscle_key)
                        
                        if not muscle_name_zh:
                            logger.warning(f"未找到肌肉映射: {muscle_key}")
                            continue
                        
                        # 检查是否已存在数据（幂等性）
                        exists = await self._check_volume_data_exists(session, muscle_name_zh)
                        
                        if exists:
                            logger.debug(f"跳过已存在数据的肌肉: {muscle_name_zh}")
                            skipped_count += 1
                            continue
                        
                        # 更新节点
                        result = await self._update_muscle_volume(
                            session,
                            muscle_name_zh,
                            volume_info
                        )
                        
                        if result:
                            updated_count += 1
                            logger.info(f"✅ 更新成功: {muscle_name_zh}")
                        else:
                            logger.warning(f"⚠️ 未找到匹配的Muscle节点: {muscle_name_zh}")
                    
                    except Exception as e:
                        error_msg = f"更新肌肉 {muscle_key} 失败: {str(e)}"
                        logger.error(error_msg)
                        errors.append({
                            "stage": "update_muscle",
                            "muscle": muscle_key,
                            "error": str(e)
                        })
                
                execution_time = time.time() - start_time
                
                logger.info(f"训练量标准补充完成")
                logger.info(f"  总节点数: {total_nodes}")
                logger.info(f"  更新节点数: {updated_count}")
                logger.info(f"  跳过节点数: {skipped_count}")
                logger.info(f"  执行时间: {execution_time:.2f}秒")
                
                return SupplementResult(
                    total_nodes=total_nodes,
                    updated_nodes=updated_count,
                    errors=errors,
                    execution_time=execution_time
                )
        
        except Exception as e:
            logger.error(f"训练量标准补充失败: {e}", exc_info=True)
            execution_time = time.time() - start_time
            return SupplementResult(
                total_nodes=0,
                updated_nodes=0,
                errors=[{"stage": "training_volume_supplement", "error": str(e)}],
                execution_time=execution_time
            )
    
    def _load_volume_data(self) -> Dict[str, Any]:
        """
        加载训练量数据
        
        Returns:
            Dict: 训练量数据
        """
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 提取volume_landmarks部分
            volume_landmarks = data.get('volume_landmarks', {})
            
            # 处理shoulders的嵌套结构
            processed_data = {}
            for key, value in volume_landmarks.items():
                if key == 'shoulders':
                    # 展开shoulders的子部分
                    for sub_key, sub_value in value.items():
                        if sub_key != 'optimal_frequency':
                            processed_data[sub_key] = sub_value
                else:
                    processed_data[key] = value
            
            logger.info(f"成功加载 {len(processed_data)} 个肌群的训练量数据")
            return processed_data
        
        except FileNotFoundError:
            logger.error(f"数据文件不存在: {self.data_file}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return {}
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            return {}
    
    async def _count_muscle_nodes(self, session) -> int:
        """统计Muscle节点总数"""
        query = "MATCH (m:Muscle) RETURN count(m) as total"
        result = await session.run(query)
        record = await result.single()
        return record["total"] if record else 0
    
    async def _check_volume_data_exists(self, session, muscle_name_zh: str) -> bool:
        """
        检查Muscle节点是否已有训练量数据（幂等性）
        
        Args:
            session: Neo4j会话
            muscle_name_zh: 肌肉中文名称
            
        Returns:
            bool: 是否已存在数据
        """
        query = """
        MATCH (m:Muscle {name_zh: $name_zh})
        WHERE m.mev IS NOT NULL AND m.mev <> 'N/A'
        RETURN count(m) > 0 as exists
        """
        result = await session.run(query, {"name_zh": muscle_name_zh})
        record = await result.single()
        return record["exists"] if record else False
    
    async def _update_muscle_volume(
        self,
        session,
        muscle_name_zh: str,
        volume_info: Dict[str, Any]
    ) -> bool:
        """
        更新Muscle节点的训练量属性
        
        Args:
            session: Neo4j会话
            muscle_name_zh: 肌肉中文名称
            volume_info: 训练量信息
            
        Returns:
            bool: 是否更新成功
        """
        # 提取训练量数值（取范围的中间值）
        mev = self._extract_volume_value(volume_info.get('MEV', {}))
        mav = self._extract_volume_value(volume_info.get('MAV', {}))
        mrv = self._extract_volume_value(volume_info.get('MRV', {}))
        mv = self._extract_volume_value(volume_info.get('MV', {}))
        optimal_frequency = volume_info.get('optimal_frequency', 'N/A')
        
        # 验证数值关系：mev < mav < mrv
        if mev and mav and mrv:
            if not (mev < mav < mrv):
                logger.warning(
                    f"训练量数值关系不正确: {muscle_name_zh} "
                    f"(MEV={mev}, MAV={mav}, MRV={mrv})"
                )
        
        query = """
        MATCH (m:Muscle {name_zh: $name_zh})
        SET m.mev = $mev,
            m.mav = $mav,
            m.mrv = $mrv,
            m.mv = $mv,
            m.optimal_frequency = $optimal_frequency,
            m.volume_data_updated_at = datetime()
        RETURN count(m) as updated_count
        """
        
        result = await session.run(query, {
            "name_zh": muscle_name_zh,
            "mev": mev,
            "mav": mav,
            "mrv": mrv,
            "mv": mv,
            "optimal_frequency": optimal_frequency
        })
        
        record = await result.single()
        return record["updated_count"] > 0 if record else False
    
    def _extract_volume_value(self, volume_dict: Dict[str, Any]) -> Optional[int]:
        """
        从训练量字典中提取数值（取范围的中间值）
        
        Args:
            volume_dict: 训练量字典，包含sets_per_week字段
            
        Returns:
            Optional[int]: 训练量数值（组/周）
        """
        if not volume_dict:
            return None
        
        sets_per_week = volume_dict.get('sets_per_week', '')
        
        if not sets_per_week or sets_per_week == '0':
            return 0
        
        # 处理范围值（如"8-10"）
        if '-' in str(sets_per_week):
            try:
                parts = str(sets_per_week).split('-')
                low = int(parts[0])
                high = int(parts[1].rstrip('+'))
                return (low + high) // 2
            except (ValueError, IndexError):
                logger.warning(f"无法解析训练量范围: {sets_per_week}")
                return None
        
        # 处理单一数值
        try:
            return int(str(sets_per_week).rstrip('+'))
        except ValueError:
            logger.warning(f"无法解析训练量数值: {sets_per_week}")
            return None
