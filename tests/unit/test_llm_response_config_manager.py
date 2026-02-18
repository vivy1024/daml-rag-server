"""
LLM响应配置管理器单元测试

测试LLMResponseConfig和LLMResponseConfigManager的核心功能
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from src.framework.config.llm_response_config_manager import (
    LLMResponseConfig,
    LLMResponseConfigManager
)


class TestLLMResponseConfig:
    """测试LLMResponseConfig数据类"""
    
    def test_create_valid_config(self):
        """测试创建有效的配置对象"""
        config = LLMResponseConfig(
            max_tokens=1000,
            temperature=0.7,
            response_style="concise",
            tone="friendly",
            length_constraint="1-2句话",
            prompt_template="测试模板: {query}"
        )
        
        assert config.max_tokens == 1000
        assert config.temperature == 0.7
        assert config.response_style == "concise"
        assert config.tone == "friendly"
    
    def test_max_tokens_validation(self):
        """测试max_tokens参数验证"""
        # 测试过小的值
        with pytest.raises(ValueError, match="max_tokens必须在50-20000之间"):
            LLMResponseConfig(
                max_tokens=10,
                temperature=0.7,
                response_style="concise",
                tone="friendly",
                length_constraint="短",
                prompt_template="test"
            )
        
        # 测试过大的值
        with pytest.raises(ValueError, match="max_tokens必须在50-20000之间"):
            LLMResponseConfig(
                max_tokens=30000,
                temperature=0.7,
                response_style="concise",
                tone="friendly",
                length_constraint="长",
                prompt_template="test"
            )
    
    def test_temperature_validation(self):
        """测试temperature参数验证"""
        # 测试负值
        with pytest.raises(ValueError, match="temperature必须在0.0-1.0之间"):
            LLMResponseConfig(
                max_tokens=1000,
                temperature=-0.1,
                response_style="concise",
                tone="friendly",
                length_constraint="短",
                prompt_template="test"
            )
        
        # 测试超过1.0的值
        with pytest.raises(ValueError, match="temperature必须在0.0-1.0之间"):
            LLMResponseConfig(
                max_tokens=1000,
                temperature=1.5,
                response_style="concise",
                tone="friendly",
                length_constraint="长",
                prompt_template="test"
            )
    
    def test_from_dict(self):
        """测试从字典创建配置"""
        data = {
            "max_tokens": 800,
            "temperature": 0.6,
            "response_style": "detailed",
            "tone": "professional",
            "length_constraint": "2-3段话",
            "prompt_template": "模板: {query}"
        }
        
        config = LLMResponseConfig.from_dict(data)
        
        assert config.max_tokens == 800
        assert config.temperature == 0.6
        assert config.response_style == "detailed"
    
    def test_to_dict(self):
        """测试转换为字典"""
        config = LLMResponseConfig(
            max_tokens=1000,
            temperature=0.7,
            response_style="concise",
            tone="friendly",
            length_constraint="1-2句话",
            prompt_template="测试: {query}"
        )
        
        data = config.to_dict()
        
        assert data["max_tokens"] == 1000
        assert data["temperature"] == 0.7
        assert data["response_style"] == "concise"
        assert "prompt_template" in data


class TestLLMResponseConfigManager:
    """测试LLMResponseConfigManager管理器类"""
    
    def test_load_from_valid_yaml(self):
        """测试从有效的YAML文件加载配置"""
        # 创建临时YAML文件
        yaml_content = """
templates:
  greeting:
    max_tokens: 100
    temperature: 0.8
    response_style: "concise"
    tone: "friendly"
    length_constraint: "1-2句话"
    prompt_template: "你好: {query}"
  
  quick_consultation:
    max_tokens: 800
    temperature: 0.6
    response_style: "concise"
    tone: "professional"
    length_constraint: "2-3段话"
    prompt_template: "咨询: {query}"

default:
  max_tokens: 2000
  temperature: 0.7
  response_style: "balanced"
  tone: "professional"
  length_constraint: "适中"
  prompt_template: "默认: {query}"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            manager = LLMResponseConfigManager(config_path=temp_path)
            
            # 验证加载的配置
            assert len(manager.configs) == 2
            assert "greeting" in manager.configs
            assert "quick_consultation" in manager.configs
            
            # 验证greeting配置
            greeting_config = manager.get_config("greeting")
            assert greeting_config.max_tokens == 100
            assert greeting_config.temperature == 0.8
            
            # 验证默认配置
            assert manager.default_config is not None
            assert manager.default_config.max_tokens == 2000
        
        finally:
            Path(temp_path).unlink()
    
    def test_load_from_nonexistent_file(self):
        """测试从不存在的文件加载配置（应抛出FileNotFoundError）"""
        with pytest.raises(FileNotFoundError):
            manager = LLMResponseConfigManager(config_path="/nonexistent/path/config.yaml")
    
    def test_get_config_existing_template(self):
        """测试获取存在的模板配置"""
        manager = LLMResponseConfigManager()

        config = manager.get_config("greeting")

        assert config is not None
        assert config.max_tokens == 200
        assert config.temperature == 0.8
    
    def test_get_config_nonexistent_template(self):
        """测试获取不存在的模板配置（应返回默认配置）"""
        manager = LLMResponseConfigManager()
        
        config = manager.get_config("unknown_template")
        
        assert config is not None
        assert config == manager.default_config
    
    def test_build_prompt_with_all_placeholders(self):
        """测试使用所有占位符构建提示词"""
        manager = LLMResponseConfigManager()
        
        prompt = manager.build_prompt(
            "greeting",
            query="你好",
            response_hint="简短友好"
        )
        
        assert "你好" in prompt
        assert "简短友好" in prompt
        assert len(prompt) > 0
    
    def test_build_prompt_missing_placeholder(self):
        """测试缺少占位符时的处理（应返回原始模板）"""
        yaml_content = """
templates:
  test_template:
    max_tokens: 100
    temperature: 0.7
    response_style: "concise"
    tone: "friendly"
    length_constraint: "短"
    prompt_template: "查询: {query}, 提示: {response_hint}"

default:
  max_tokens: 2000
  temperature: 0.7
  response_style: "balanced"
  tone: "professional"
  length_constraint: "适中"
  prompt_template: "默认"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            manager = LLMResponseConfigManager(config_path=temp_path)
            
            # 只提供部分占位符
            prompt = manager.build_prompt(
                "test_template",
                query="测试"
                # 缺少response_hint
            )
            
            # 应该返回原始模板（因为缺少占位符）
            assert "查询" in prompt or "query" in prompt
        
        finally:
            Path(temp_path).unlink()
    
    def test_reload_config(self):
        """测试配置热加载"""
        # 创建初始配置文件
        yaml_content_v1 = """
templates:
  greeting:
    max_tokens: 100
    temperature: 0.8
    response_style: "concise"
    tone: "friendly"
    length_constraint: "1-2句话"
    prompt_template: "版本1: {query}"

default:
  max_tokens: 2000
  temperature: 0.7
  response_style: "balanced"
  tone: "professional"
  length_constraint: "适中"
  prompt_template: "默认"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write(yaml_content_v1)
            temp_path = f.name
        
        try:
            manager = LLMResponseConfigManager(config_path=temp_path)
            
            # 验证初始配置
            config_v1 = manager.get_config("greeting")
            assert config_v1.max_tokens == 100
            
            # 修改配置文件
            yaml_content_v2 = """
templates:
  greeting:
    max_tokens: 200
    temperature: 0.9
    response_style: "concise"
    tone: "friendly"
    length_constraint: "1-2句话"
    prompt_template: "版本2: {query}"

default:
  max_tokens: 2000
  temperature: 0.7
  response_style: "balanced"
  tone: "professional"
  length_constraint: "适中"
  prompt_template: "默认"
"""
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(yaml_content_v2)
            
            # 重新加载配置
            manager.reload()
            
            # 验证更新后的配置
            config_v2 = manager.get_config("greeting")
            assert config_v2.max_tokens == 200
            assert config_v2.temperature == 0.9
        
        finally:
            Path(temp_path).unlink()
    
    def test_get_all_template_ids(self):
        """测试获取所有模板ID"""
        manager = LLMResponseConfigManager()
        
        template_ids = manager.get_all_template_ids()
        
        assert isinstance(template_ids, list)
        assert len(template_ids) > 0
        assert "greeting" in template_ids
    
    def test_has_config(self):
        """测试检查模板配置是否存在"""
        manager = LLMResponseConfigManager()
        
        assert manager.has_config("greeting") is True
        assert manager.has_config("unknown_template") is False
    
    def test_invalid_yaml_format(self):
        """测试无效的YAML格式（应抛出ValueError）"""
        invalid_yaml = """
templates:
  greeting:
    max_tokens: 100
    temperature: invalid_value  # 无效的值
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write(invalid_yaml)
            temp_path = f.name
        
        try:
            # 应该抛出ValueError，因为配置格式无效
            with pytest.raises(ValueError):
                manager = LLMResponseConfigManager(config_path=temp_path)
        
        finally:
            Path(temp_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
