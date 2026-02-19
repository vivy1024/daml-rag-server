"""
LLM响应配置管理器

提供基于YAML配置文件的LLM响应配置管理功能，支持：
- 从YAML文件加载配置
- 根据模板ID获取配置
- 动态构建提示词
- 热加载配置（可选）

版本: v1.0.0
创建日期: 2025-12-17
"""

import os
import yaml
import logging
from dataclasses import dataclass, asdict
from typing import Dict, Optional
from pathlib import Path

# 延迟导入避免循环依赖
_persona_manager = None

def _get_persona_manager():
    """延迟获取 PersonaManager 单例"""
    global _persona_manager
    if _persona_manager is None:
        try:
            from ...applications.fitness.config.system_persona import get_persona_manager
            _persona_manager = get_persona_manager()
        except Exception as e:
            logging.getLogger(__name__).warning(f"PersonaManager 加载失败: {e}")
    return _persona_manager

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# 前端渲染格式约束（追加到所有 DAG 模板的 system prompt 末尾）
# ═══════════════════════════════════════════════════════════

_RENDERING_FORMAT_CONSTRAINT = """

## 📐 输出格式要求（前端渲染）

你的回答将直接在移动端App中以Markdown渲染，必须严格遵守以下格式：

1. **使用标准Markdown**：标题用 ##/###，列表用 -/1.，加粗用 **文字**
2. **适当使用emoji**：每个主要段落标题前加一个相关emoji（如 💪🏋️🥗⚠️📊）
3. **结构清晰**：用空行分隔段落，避免超长段落（每段不超过4-5行）
4. **禁止HTML标签**：不要输出任何HTML（如<br>、<div>等）
5. **禁止代码块**：不要使用```包裹普通文本内容
6. **数据表格**：简单对比用Markdown表格（| 列1 | 列2 |），复杂数据用列表
7. **安全提醒醒目**：安全/禁忌信息用 > ⚠️ 引用块格式"""


@dataclass
class LLMResponseConfig:
    """
    LLM响应配置数据类
    
    定义单个DAG模板的LLM响应行为，包括：
    - max_tokens: 最大生成token数
    - temperature: 温度参数（0.0-1.0）
    - response_style: 响应风格（concise/detailed/comprehensive等）
    - tone: 语气（friendly/professional/cautious等）
    - length_constraint: 长度约束描述
    - prompt_template: 提示词模板（支持占位符）
    - stream: 是否启用流式输出（可选，默认False）
    """
    max_tokens: int
    temperature: float
    response_style: str
    tone: str
    length_constraint: str
    prompt_template: str
    stream: bool = False  # 新增：是否启用流式输出
    
    def __post_init__(self):
        """验证参数范围"""
        if not (50 <= self.max_tokens <= 20000):
            raise ValueError(f"max_tokens必须在50-20000之间，当前值: {self.max_tokens}")
        
        if not (0.0 <= self.temperature <= 1.0):
            raise ValueError(f"temperature必须在0.0-1.0之间，当前值: {self.temperature}")
    
    @classmethod
    def from_dict(cls, data: dict) -> 'LLMResponseConfig':
        """从字典创建配置对象"""
        return cls(**data)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)


class LLMResponseConfigManager:
    """
    LLM响应配置管理器
    
    负责：
    1. 从YAML文件加载所有模板的配置
    2. 提供根据模板ID获取配置的接口
    3. 提供动态构建提示词的接口
    4. 支持配置热加载（可选）
    
    使用示例：
        manager = LLMResponseConfigManager()
        config = manager.get_config("greeting")
        prompt = manager.build_prompt("greeting", query="你好", response_hint="简短友好")
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: YAML配置文件路径，默认为 config/llm_response_config.yaml
        """
        if config_path is None:
            # 默认配置文件路径：相对于项目根目录
            project_root = Path(__file__).parent.parent.parent.parent
            config_path = project_root / "config" / "llm_response_config.yaml"
        
        self.config_path = Path(config_path)
        self.configs: Dict[str, LLMResponseConfig] = {}
        self.default_config: Optional[LLMResponseConfig] = None
        self.last_modified: Optional[float] = None  # 文件最后修改时间
        
        # 加载配置
        self._load_configs()
    
    def _load_configs(self):
        """
        从YAML文件加载配置
        
        加载所有模板配置和默认配置。如果文件不存在或格式错误，
        抛出异常而不是降级到默认配置。
        """
        try:
            if not self.config_path.exists():
                error_msg = f"❌ 配置文件不存在: {self.config_path}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                error_msg = f"❌ 配置文件为空: {self.config_path}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # 验证配置结构
            self._validate_config(data)
            
            # 加载模板配置
            templates = data.get('templates', {})
            loaded_count = 0
            for template_id, config_data in templates.items():
                try:
                    self.configs[template_id] = LLMResponseConfig.from_dict(config_data)
                    logger.debug(f"✅ 加载配置: {template_id}")
                    loaded_count += 1
                except Exception as e:
                    logger.error(f"❌ 加载模板配置失败 {template_id}: {e}")
                    raise ValueError(f"模板配置 '{template_id}' 格式错误: {e}")
            
            # 加载默认配置
            if 'default' in data:
                try:
                    self.default_config = LLMResponseConfig.from_dict(data['default'])
                    logger.debug("✅ 加载默认配置成功")
                except Exception as e:
                    logger.error(f"❌ 加载默认配置失败: {e}")
                    raise ValueError(f"默认配置格式错误: {e}")
            else:
                self._create_fallback_default()
            
            # 记录文件修改时间
            self.last_modified = self.config_path.stat().st_mtime
            
            logger.info(f"✅ 配置加载完成: {len(self.configs)}个模板配置")
            
        except yaml.YAMLError as e:
            # 提取详细的错误信息
            error_details = self._extract_yaml_error_details(e)
            error_msg = f"❌ YAML格式错误:\n{error_details}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        except (FileNotFoundError, ValueError):
            # 重新抛出已知错误
            raise
        except Exception as e:
            error_msg = f"❌ 加载配置文件失败: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _extract_yaml_error_details(self, error: yaml.YAMLError) -> str:
        """
        提取YAML错误的详细信息
        
        Args:
            error: YAML解析错误对象
        
        Returns:
            str: 格式化的错误信息，包含文件路径、行号、列号
        """
        details = [f"文件: {self.config_path}"]
        
        # 提取问题标记（行号和列号）
        if hasattr(error, 'problem_mark'):
            mark = error.problem_mark
            details.append(f"行号: {mark.line + 1}")
            details.append(f"列号: {mark.column + 1}")
            
            # 如果有上下文标记，也显示
            if hasattr(error, 'context_mark'):
                context_mark = error.context_mark
                details.append(f"上下文行号: {context_mark.line + 1}")
        
        # 提取问题描述
        if hasattr(error, 'problem'):
            details.append(f"问题: {error.problem}")
        
        # 提取上下文描述
        if hasattr(error, 'context'):
            details.append(f"上下文: {error.context}")
        
        return "\n".join(details)
    
    def _validate_config(self, data: dict):
        """
        验证配置文件的结构完整性
        
        Args:
            data: 从YAML加载的配置数据
        
        Raises:
            ValueError: 如果配置结构不完整
        """
        # 检查必需的顶层键
        if 'templates' not in data:
            raise ValueError("配置文件缺少必需的 'templates' 键")
        
        templates = data.get('templates', {})
        if not isinstance(templates, dict):
            raise ValueError("'templates' 必须是字典类型")
        
        if len(templates) == 0:
            raise ValueError("'templates' 不能为空，至少需要一个模板配置")
        
        # 验证每个模板的必需字段
        required_fields = ['max_tokens', 'temperature', 'response_style', 'tone', 'length_constraint', 'prompt_template']
        
        for template_id, config_data in templates.items():
            if not isinstance(config_data, dict):
                raise ValueError(f"模板 '{template_id}' 的配置必须是字典类型")
            
            missing_fields = [field for field in required_fields if field not in config_data]
            if missing_fields:
                raise ValueError(f"模板 '{template_id}' 缺少必需字段: {', '.join(missing_fields)}")
        
        logger.debug("✅ 配置结构验证通过")
    

    
    def _create_fallback_default(self):
        """创建兜底的默认配置"""
        self.default_config = LLMResponseConfig(
            max_tokens=2000,
            temperature=0.7,
            response_style="balanced",
            tone="professional",
            length_constraint="适中",
            prompt_template="""## 任务
根据用户查询提供专业的分析和建议。

用户查询: {query}

用户档案: {user_profile}

## 约束
- 禁止编造用户档案信息
- 提供通用的专业建议"""
        )
    
    def get_config(self, template_id: str) -> LLMResponseConfig:
        """
        获取指定模板的配置
        
        在获取配置前会自动检查文件是否被修改，如果是则重新加载。
        
        Args:
            template_id: DAG模板ID（如"greeting", "quick_consultation"）
        
        Returns:
            LLMResponseConfig: 模板配置对象，如果模板不存在则返回默认配置
        """
        # 检查配置文件是否被修改
        self.reload_if_modified()
        
        config = self.configs.get(template_id)
        
        if config is None:
            logger.warning(f"⚠️ 模板配置不存在: {template_id}，使用默认配置")
            return self.default_config
        
        return config
    
    def build_prompt(self, template_id: str, persona_id: str = None, **kwargs) -> str:
        """
        使用模板生成提示词（三层组装）

        三层结构：
        1. persona.system_prefix（怎么说）— 来自 SystemPersona
        2. template.task_instruction（做什么）— 来自 DAG 模板
        3. _RENDERING_FORMAT_CONSTRAINT（怎么排版）— 固定追加

        Args:
            template_id: DAG模板ID
            persona_id: 人设ID（可选，默认使用 coach_professional）
            **kwargs: 提示词模板的占位符参数，常用参数包括：
                - query: 用户查询文本
                - user_profile: 用户档案（字典或JSON字符串）
                - response_hint: 响应提示
                - mcp_tools_count: MCP工具调用数量
                - retrieval_count: 检索结果数量
                - mcp_tools_result: MCP工具结果JSON字符串

        Returns:
            str: 构建好的提示词

        示例：
            prompt = manager.build_prompt(
                "greeting",
                persona_id="coach_friendly",
                query="你好",
                response_hint="简短友好，1-2句话"
            )
        """
        config = self.get_config(template_id)

        try:
            # Layer 2: 任务指令（模板变量替换）
            task_prompt = config.prompt_template
            for key, value in kwargs.items():
                placeholder = "{" + key + "}"
                if placeholder in task_prompt:
                    str_value = str(value) if value is not None else ""
                    task_prompt = task_prompt.replace(placeholder, str_value)

            # Layer 1: Persona 风格前缀
            persona_prefix = ""
            pm = _get_persona_manager()
            if pm:
                persona = pm.get_persona(persona_id)
                persona_prefix = persona.system_prefix
            else:
                logger.debug("PersonaManager 不可用，跳过 Persona 注入")

            # 三层拼接
            if persona_prefix:
                prompt = f"{persona_prefix}\n\n{task_prompt}\n{_RENDERING_FORMAT_CONSTRAINT}"
            else:
                prompt = f"{task_prompt}\n{_RENDERING_FORMAT_CONSTRAINT}"

            return prompt
        except Exception as e:
            logger.error(f"构建提示词失败: {e}")
            return config.prompt_template
    
    def build_messages(
        self,
        template_id: str,
        query: str,
        user_profile: str = "未提供",
        response_hint: str = "",
        mcp_tools_result: str = "{}",
        retrieval_results: list = None
    ) -> list:
        """
        构建LLM消息列表（用于流式调用）
        
        将各种输入参数组合成符合OpenAI API标准的消息列表格式，
        用于流式LLM调用（call_deepseek_stream）。
        
        Args:
            template_id: DAG模板ID
            query: 用户查询文本
            user_profile: 用户档案JSON字符串，默认"未提供"
            response_hint: 响应提示，来自DAG模板的response_hint
            mcp_tools_result: MCP工具结果JSON字符串，默认"{}"
            retrieval_results: 检索结果列表，默认None
        
        Returns:
            list: 消息列表，格式为 [{"role": "system/user/assistant", "content": "..."}]
        
        示例：
            messages = manager.build_messages(
                template_id="complete_training_plan",
                query="帮我设计一个增肌计划",
                user_profile='{"age": 25, "experience": "intermediate"}',
                response_hint="请提供完整的4周训练计划",
                mcp_tools_result='{"program": {...}}',
                retrieval_results=[...]
            )
        """
        # 获取配置
        config = self.get_config(template_id)
        
        # 构建系统提示词
        system_prompt = f"""你是一位专业的健身教练和营养师，拥有丰富的训练计划设计经验。

{config.prompt_template}

**响应要求**:
- 响应风格: {config.response_style}
- 语气: {config.tone}
- 长度约束: {config.length_constraint}

{response_hint}

请基于以下信息提供专业的分析和建议。"""
        
        # 构建用户消息
        user_content = f"""**用户查询**: {query}

**用户档案**:
{user_profile}

**MCP工具分析结果**:
{mcp_tools_result}
"""
        
        # 如果有检索结果，添加到用户消息中
        if retrieval_results and len(retrieval_results) > 0:
            user_content += "\n**相关推荐**:\n"
            for i, result in enumerate(retrieval_results[:5], 1):
                name = result.get('name', result.get('title', '未知'))
                description = result.get('description', result.get('summary', ''))
                user_content += f"{i}. {name}"
                if description:
                    user_content += f" - {description[:100]}"
                user_content += "\n"
        
        # 构建消息列表
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        logger.debug(f"构建消息列表完成: template_id={template_id}, messages_count={len(messages)}")
        
        return messages
    
    def reload_if_modified(self) -> bool:
        """
        检查配置文件是否被修改，如果是则重新加载
        
        Returns:
            bool: 如果配置被重新加载返回True，否则返回False
        """
        try:
            if not self.config_path.exists():
                logger.warning(f"配置文件不存在: {self.config_path}")
                return False
            
            current_mtime = self.config_path.stat().st_mtime
            
            # 如果文件未修改，直接返回
            if self.last_modified is not None and current_mtime == self.last_modified:
                return False
            
            # 文件已修改，重新加载
            logger.info(f"🔄 检测到配置文件修改，重新加载: {self.config_path}")
            self.reload()
            return True
            
        except Exception as e:
            logger.error(f"❌ 检查配置文件修改时出错: {e}")
            return False
    
    def reload(self):
        """
        强制重新加载配置（热加载）
        
        清空当前配置并重新从文件加载，用于在不重启服务的情况下更新配置
        """
        logger.info("🔄 重新加载配置...")
        self.configs.clear()
        self.default_config = None
        self.last_modified = None
        self._load_configs()
        logger.info("✅ 配置重新加载完成")
    
    def get_all_template_ids(self) -> list:
        """
        获取所有已配置的模板ID列表
        
        Returns:
            list: 模板ID列表
        """
        return list(self.configs.keys())
    
    def has_config(self, template_id: str) -> bool:
        """
        检查指定模板是否有配置
        
        Args:
            template_id: DAG模板ID
        
        Returns:
            bool: 如果存在配置返回True，否则返回False
        """
        return template_id in self.configs


# 全局单例实例（可选）
_global_manager: Optional[LLMResponseConfigManager] = None


def get_global_config_manager() -> LLMResponseConfigManager:
    """
    获取全局配置管理器单例
    
    Returns:
        LLMResponseConfigManager: 全局配置管理器实例
    """
    global _global_manager
    if _global_manager is None:
        _global_manager = LLMResponseConfigManager()
    return _global_manager
