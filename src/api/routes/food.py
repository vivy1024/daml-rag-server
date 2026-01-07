# -*- coding: utf-8 -*-
"""
Food API Routes

食物数据查询接口，提供：
- 食物列表查询（支持分页、搜索、分类筛选）
- 食物详情查询
- 食物分类列表

数据来源：《中国食物成分表》
数据文件：data/nutrition/core/chinese_nutrition_db.json

版本：v1.0.0
创建日期：2026-01-01
"""

import json
import os
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/food", tags=["Food"])

# 数据缓存
_food_data_cache: Optional[Dict[str, Any]] = None
_food_list_cache: Optional[List[Dict[str, Any]]] = None


class FoodBasic(BaseModel):
    """食物基本信息"""
    id: str
    name: str
    category: str
    calories: float
    protein: float
    fat: float
    carbs: float
    fiber: Optional[float] = None
    gi_value: Optional[int] = None
    price_level: Optional[str] = None


class FoodDetail(FoodBasic):
    """食物详细信息"""
    # 矿物质
    calcium: Optional[float] = None
    iron: Optional[float] = None
    zinc: Optional[float] = None
    selenium: Optional[float] = None
    potassium: Optional[float] = None
    phosphorus: Optional[float] = None
    
    # 维生素
    vitamin_a: Optional[float] = None
    vitamin_c: Optional[float] = None
    vitamin_b1: Optional[float] = None
    vitamin_b2: Optional[float] = None
    vitamin_b6: Optional[float] = None
    vitamin_b12: Optional[float] = None
    vitamin_d: Optional[float] = None
    vitamin_e: Optional[float] = None
    vitamin_k: Optional[float] = None
    niacin: Optional[float] = None
    folate: Optional[float] = None
    
    # 其他
    cholesterol: Optional[float] = None
    antioxidant_level: Optional[str] = None
    protein_score: Optional[str] = None
    omega3: Optional[str] = None
    
    # 元数据
    source: Optional[str] = None


class FoodCategory(BaseModel):
    """食物分类"""
    id: str
    name: str
    count: int


class PaginationInfo(BaseModel):
    """分页信息"""
    current: int
    pageSize: int
    total: int
    totalPages: int


class FoodListResponse(BaseModel):
    """食物列表响应"""
    items: List[FoodBasic]
    pagination: PaginationInfo
    categories: List[FoodCategory]


def load_food_data() -> Dict[str, Any]:
    """加载食物数据"""
    global _food_data_cache
    
    if _food_data_cache is not None:
        return _food_data_cache
    
    # 获取数据文件路径
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    data_file = os.path.join(base_dir, "data", "nutrition", "core", "chinese_nutrition_db.json")
    
    try:
        with open(data_file, "r", encoding="utf-8") as f:
            _food_data_cache = json.load(f)
        return _food_data_cache
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="食物数据文件不存在")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="食物数据文件格式错误")


def get_food_list() -> List[Dict[str, Any]]:
    """获取扁平化的食物列表"""
    global _food_list_cache
    
    if _food_list_cache is not None:
        return _food_list_cache
    
    data = load_food_data()
    foods_db = data.get("chinese_foods_db", {})
    
    food_list = []
    for category, foods in foods_db.items():
        for name, nutrition in foods.items():
            food_item = {
                "id": f"{category}_{name}",
                "name": name,
                "category": category,
                "calories": nutrition.get("热量", 0),
                "protein": nutrition.get("蛋白质", 0),
                "fat": nutrition.get("脂肪", 0),
                "carbs": nutrition.get("碳水", nutrition.get("碳水化合物", 0)),
                "fiber": nutrition.get("膳食纤维"),
                "gi_value": nutrition.get("GI值"),
                "price_level": nutrition.get("价格等级"),
                # 矿物质
                "calcium": nutrition.get("钙"),
                "iron": nutrition.get("铁"),
                "zinc": nutrition.get("锌"),
                "selenium": nutrition.get("硒"),
                "potassium": nutrition.get("钾"),
                "phosphorus": nutrition.get("磷"),
                # 维生素
                "vitamin_a": nutrition.get("维生素A"),
                "vitamin_c": nutrition.get("维生素C"),
                "vitamin_b1": nutrition.get("维生素B1"),
                "vitamin_b2": nutrition.get("维生素B2"),
                "vitamin_b6": nutrition.get("维生素B6"),
                "vitamin_b12": nutrition.get("维生素B12"),
                "vitamin_d": nutrition.get("维生素D"),
                "vitamin_e": nutrition.get("维生素E"),
                "vitamin_k": nutrition.get("维生素K"),
                "niacin": nutrition.get("烟酸"),
                "folate": nutrition.get("叶酸"),
                # 其他
                "cholesterol": nutrition.get("胆固醇"),
                "antioxidant_level": nutrition.get("抗氧化等级"),
                "protein_score": nutrition.get("蛋白质评分"),
                "omega3": nutrition.get("omega-3"),
            }
            food_list.append(food_item)
    
    _food_list_cache = food_list
    return _food_list_cache


@router.get("", response_model=FoodListResponse)
async def get_foods(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    category: Optional[str] = Query(None, description="分类筛选"),
):
    """
    获取食物列表
    
    支持分页、搜索和分类筛选
    """
    food_list = get_food_list()
    
    # 筛选
    filtered_foods = food_list
    
    # 分类筛选
    if category:
        filtered_foods = [f for f in filtered_foods if f["category"] == category]
    
    # 搜索筛选
    if search:
        search_lower = search.lower()
        filtered_foods = [
            f for f in filtered_foods 
            if search_lower in f["name"].lower() or search_lower in f["category"].lower()
        ]
    
    # 计算分页
    total = len(filtered_foods)
    total_pages = (total + page_size - 1) // page_size
    start = (page - 1) * page_size
    end = start + page_size
    
    # 获取当前页数据
    page_items = filtered_foods[start:end]
    
    # 构建分类统计
    category_counts: Dict[str, int] = {}
    for f in food_list:
        cat = f["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    categories = [
        FoodCategory(id=cat, name=cat, count=count)
        for cat, count in category_counts.items()
    ]
    
    return FoodListResponse(
        items=[FoodBasic(**f) for f in page_items],
        pagination=PaginationInfo(
            current=page,
            pageSize=page_size,
            total=total,
            totalPages=total_pages,
        ),
        categories=categories,
    )


@router.get("/categories", response_model=List[FoodCategory])
async def get_categories():
    """
    获取食物分类列表
    """
    food_list = get_food_list()
    
    # 统计各分类数量
    category_counts: Dict[str, int] = {}
    for f in food_list:
        cat = f["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    return [
        FoodCategory(id=cat, name=cat, count=count)
        for cat, count in category_counts.items()
    ]


@router.get("/{food_id}", response_model=FoodDetail)
async def get_food_detail(food_id: str):
    """
    获取食物详情
    
    food_id 格式：{category}_{name}
    """
    food_list = get_food_list()
    
    # 查找食物
    for food in food_list:
        if food["id"] == food_id:
            return FoodDetail(
                **food,
                source="《中国食物成分表》"
            )
    
    raise HTTPException(status_code=404, detail="食物不存在")
