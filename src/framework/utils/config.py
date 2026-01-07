"""
Configuration classes for DAML-RAG Framework.

This module provides configuration classes for various components:
- LLMConfig: LLM provider configuration
- DomainConfig: Domain-specific configuration
- ToolCacheConfig: Tool caching configuration
- ModelConfig: Model selection configuration
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class CacheLevel(Enum):
    """Cache level enumeration."""
    L1_MEMORY = "memory"
    L2_REDIS = "redis"
    L3_DISK = "disk"


@dataclass
class LLMConfig:
    """
    LLM configuration class.
    
    Attributes:
        provider: LLM provider name (e.g., "openai", "deepseek", "ollama", "custom")
        api_key: API key for the provider
        base_url: Base URL for API endpoint
        model: Model name/identifier
        timeout: Request timeout in seconds
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature
        system_prompt: Optional system prompt
    """
    provider: str
    api_key: str
    base_url: str
    model: str
    timeout: float = 60.0
    max_tokens: int = 2000
    temperature: float = 0.7
    system_prompt: Optional[str] = None


@dataclass
class DomainConfig:
    """
    Domain-specific configuration.
    
    Attributes:
        keyword_mapping: Mapping of keywords to synonyms
        business_rules: Business rule definitions
        validation_rules: Validation rule functions
    """
    keyword_mapping: Dict[str, List[str]] = field(default_factory=dict)
    business_rules: Dict[str, Any] = field(default_factory=dict)
    validation_rules: Dict[str, Callable] = field(default_factory=dict)


@dataclass
class ToolCacheConfig:
    """
    Tool cache configuration.
    
    Attributes:
        ttl: Time-to-live in seconds
        preload: Whether to preload cache
        level: Cache level (memory, redis, disk)
    """
    ttl: int
    preload: bool
    level: CacheLevel


@dataclass
class ModelConfig:
    """
    Model configuration for adaptive model selection.
    
    Attributes:
        name: Model name
        llm_config: LLM configuration for this model
        role: Model role ("teacher" or "student")
    """
    name: str
    llm_config: LLMConfig
    role: str  # "teacher" or "student"
