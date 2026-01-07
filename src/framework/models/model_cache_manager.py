# -*- coding: utf-8 -*-
"""
ModelCacheManager - 全局模型缓存管理器

用于管理BGE等大型模型的全局缓存，避免重复加载

核心功能：
1. 单例模式：确保全局只有一个实例
2. 模型缓存：首次加载后缓存，后续直接使用
3. 线程安全：使用锁保证并发安全
4. 预加载：系统启动时预加载模型

版本: v1.0.0
日期: 2025-12-16
作者: 薛小川
"""

import logging
import threading
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ModelCacheManager:
    """
    全局模型缓存管理器（单例模式）
    
    设计原则：
    - 单例模式：全局唯一实例
    - 懒加载：首次使用时才加载模型
    - 缓存：加载后缓存，避免重复加载
    - 线程安全：使用锁保证并发安全
    
    Example:
        >>> cache = ModelCacheManager.get_instance()
        >>> model = cache.get_bge_model()
        >>> # 后续调用直接使用缓存
        >>> model = cache.get_bge_model()  # 不会重新加载
    """
    
    _instance: Optional['ModelCacheManager'] = None
    _lock = threading.Lock()
    
    def __init__(self):
        """
        私有构造函数，不应直接调用
        
        使用 get_instance() 获取单例实例
        """
        if ModelCacheManager._instance is not None:
            raise RuntimeError(
                "ModelCacheManager是单例类，请使用get_instance()获取实例"
            )
        
        # 模型缓存字典
        self._models: Dict[str, Any] = {}
        
        # 模型加载锁（保证并发安全）
        self._model_locks: Dict[str, threading.Lock] = {}
        
        logger.info("[ModelCacheManager] 初始化完成")
    
    @classmethod
    def get_instance(cls) -> 'ModelCacheManager':
        """
        获取单例实例（线程安全）
        
        Returns:
            ModelCacheManager: 单例实例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def get_bge_model(self, model_name: str = "BAAI/bge-m3"):
        """
        获取BGE模型（带缓存）
        
        Args:
            model_name: BGE模型名称，默认为BAAI/bge-m3
        
        Returns:
            SentenceTransformer: BGE模型实例，如果加载失败返回None
        
        Example:
            >>> cache = ModelCacheManager.get_instance()
            >>> model = cache.get_bge_model()
            >>> if model:
            ...     embeddings = model.encode(["查询文本"])
        """
        cache_key = f"bge-{model_name}"
        
        # 如果已缓存，直接返回
        if cache_key in self._models:
            logger.info(f"✅ 使用缓存的BGE模型: {model_name}")
            return self._models[cache_key]
        
        # 获取或创建模型锁
        if cache_key not in self._model_locks:
            with self._lock:
                if cache_key not in self._model_locks:
                    self._model_locks[cache_key] = threading.Lock()
        
        # 加载模型（线程安全）
        with self._model_locks[cache_key]:
            # 双重检查（可能其他线程已加载）
            if cache_key in self._models:
                logger.info(f"✅ 使用缓存的BGE模型: {model_name}")
                return self._models[cache_key]
            
            try:
                import os
                
                logger.info(f"🔄 首次加载BGE模型: {model_name}...")
                
                # 优先使用本地缓存（避免429限流问题）
                # 检查本地缓存是否存在
                cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
                model_cache_path = os.path.join(cache_dir, f"models--{model_name.replace('/', '--')}")
                
                model = None
                
                # 如果本地缓存存在，优先使用离线模式
                if os.path.exists(model_cache_path):
                    logger.info(f"📦 检测到本地缓存: {model_cache_path}")
                    try:
                        # 在导入SentenceTransformer之前设置离线模式环境变量
                        # 这样可以确保库在初始化时就知道使用离线模式
                        os.environ["HF_HUB_OFFLINE"] = "1"
                        os.environ["TRANSFORMERS_OFFLINE"] = "1"
                        os.environ["HF_DATASETS_OFFLINE"] = "1"
                        
                        # 延迟导入，确保环境变量已设置
                        from sentence_transformers import SentenceTransformer
                        
                        # 尝试找到最新的snapshot目录
                        snapshots_dir = os.path.join(model_cache_path, "snapshots")
                        if os.path.exists(snapshots_dir):
                            snapshot_dirs = [d for d in os.listdir(snapshots_dir) 
                                           if os.path.isdir(os.path.join(snapshots_dir, d))]
                            if snapshot_dirs:
                                # 使用第一个snapshot目录的完整路径
                                local_model_path = os.path.join(snapshots_dir, snapshot_dirs[0])
                                logger.info(f"📂 使用本地模型路径: {local_model_path}")
                                model = SentenceTransformer(local_model_path)
                                logger.info(f"✅ 从本地路径加载成功: {model_name}")
                            else:
                                # 如果没有snapshot，尝试使用模型名称
                                model = SentenceTransformer(
                                    model_name, 
                                    local_files_only=True,
                                    cache_folder=cache_dir
                                )
                                logger.info(f"✅ 从本地缓存加载成功: {model_name}")
                        else:
                            model = SentenceTransformer(
                                model_name, 
                                local_files_only=True,
                                cache_folder=cache_dir
                            )
                            logger.info(f"✅ 从本地缓存加载成功: {model_name}")
                    except Exception as local_error:
                        logger.warning(f"⚠️ 本地缓存加载失败: {local_error}")
                        model = None
                    finally:
                        # 恢复环境变量
                        os.environ.pop("HF_HUB_OFFLINE", None)
                        os.environ.pop("TRANSFORMERS_OFFLINE", None)
                        os.environ.pop("HF_DATASETS_OFFLINE", None)
                
                # 如果本地加载失败，尝试在线加载
                if model is None:
                    logger.info(f"🌐 尝试在线加载: {model_name}")
                    try:
                        from sentence_transformers import SentenceTransformer
                        model = SentenceTransformer(model_name)
                        logger.info(f"✅ 在线加载成功: {model_name}")
                    except Exception as online_error:
                        logger.error(f"❌ 在线加载失败: {online_error}")
                        raise online_error
                
                # 缓存模型
                self._models[cache_key] = model
                
                logger.info(f"✅ BGE模型加载完成并缓存: {model_name}")
                return model
                
            except Exception as e:
                logger.error(f"❌ BGE模型加载失败: {model_name}, 错误: {e}")
                # 不缓存失败结果，下次可以重试
                return None
    
    def preload_models(self):
        """
        预加载所有模型
        
        在系统启动时调用，提前加载模型到内存
        
        注意：v8.72.0起，系统使用GTE-Large-zh作为主要向量模型
        BGE-M3仅用于复杂度分类，按需加载
        
        Example:
            >>> cache = ModelCacheManager.get_instance()
            >>> cache.preload_models()
        """
        logger.info("🚀 开始预加载模型...")
        
        # ✅ v8.72.0: 预加载GTE-Large-zh模型（主要向量模型）
        # BGE-M3仅用于复杂度分类，按需加载以节省启动时间
        gte_model = self.get_embedding_model("thenlper/gte-large-zh")
        
        if gte_model is not None:
            logger.info("✅ 模型预加载完成 (GTE-Large-zh)")
        else:
            logger.warning("⚠️ 模型预加载失败，将在首次使用时加载")
    
    def get_embedding_model(self, model_name: str):
        """
        获取通用Embedding模型（带缓存）
        
        支持的模型：
        - thenlper/gte-large-zh (推荐，相关性94.4%)
        - BAAI/bge-m3
        - BAAI/bge-large-zh-v1.5
        - moka-ai/m3e-large
        
        Args:
            model_name: 模型名称
        
        Returns:
            SentenceTransformer: 模型实例，如果加载失败返回None
        """
        cache_key = f"embedding-{model_name}"
        
        # 如果已缓存，直接返回
        if cache_key in self._models:
            logger.debug(f"✅ 使用缓存的Embedding模型: {model_name}")
            return self._models[cache_key]
        
        # 获取或创建模型锁
        if cache_key not in self._model_locks:
            with self._lock:
                if cache_key not in self._model_locks:
                    self._model_locks[cache_key] = threading.Lock()
        
        # 加载模型（线程安全）
        with self._model_locks[cache_key]:
            # 双重检查
            if cache_key in self._models:
                return self._models[cache_key]
            
            try:
                from sentence_transformers import SentenceTransformer
                
                logger.info(f"🔄 加载Embedding模型: {model_name}...")
                model = SentenceTransformer(model_name)
                
                # 缓存模型
                self._models[cache_key] = model
                logger.info(f"✅ Embedding模型加载完成: {model_name}")
                return model
                
            except Exception as e:
                logger.error(f"❌ Embedding模型加载失败: {model_name}, 错误: {e}")
                return None
    
    def clear_cache(self, model_key: Optional[str] = None):
        """
        清除模型缓存
        
        Args:
            model_key: 要清除的模型键，如果为None则清除所有缓存
        
        Example:
            >>> cache = ModelCacheManager.get_instance()
            >>> cache.clear_cache("bge-BAAI/bge-m3")  # 清除特定模型
            >>> cache.clear_cache()  # 清除所有模型
        """
        if model_key:
            if model_key in self._models:
                del self._models[model_key]
                logger.info(f"🗑️ 已清除模型缓存: {model_key}")
        else:
            self._models.clear()
            logger.info("🗑️ 已清除所有模型缓存")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        
        Example:
            >>> cache = ModelCacheManager.get_instance()
            >>> stats = cache.get_statistics()
            >>> print(f"已缓存模型数: {stats['cached_models_count']}")
        """
        return {
            "cached_models_count": len(self._models),
            "cached_models": list(self._models.keys()),
            "is_singleton": ModelCacheManager._instance is not None,
        }
