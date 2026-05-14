#!/bin/bash
# 批量提取教材知识到 Neo4j
# 版本: v1.0.0
# 日期: 2026-02-16

set -e

echo "=========================================="
echo "教材知识批量提取脚本"
echo "=========================================="
echo ""

# 教材文件列表（宿主机路径）
TEXTBOOKS=(
    "/f/build_body/.books/Open-Textbook-of-Exercise-Physiology-1756071395.pdf"
    "/f/build_body/.books/foundationsoffitnessprogramming_201508.pdf"
    "/f/build_body/.books/Introduction_to_Sports_Biomechanics.pdf"
    "/f/build_body/.books/AMJ-04-107.pdf"
)

# 教材名称（用于日志）
TEXTBOOK_NAMES=(
    "运动生理学开放教材"
    "NSCA Foundations of Fitness Programming"
    "运动生物力学导论"
    "AMJ论文"
)

# 临时目录（容器内）
TEMP_DIR="/app/data/temp_textbooks"

# 创建临时目录
echo "创建临时目录..."
docker exec fitness_daml_rag bash -c "mkdir -p $TEMP_DIR"

# 复制教材到容器
echo ""
echo "复制教材文件到容器..."
for i in "${!TEXTBOOKS[@]}"; do
    textbook="${TEXTBOOKS[$i]}"
    name="${TEXTBOOK_NAMES[$i]}"
    filename=$(basename "$textbook")

    echo "  [$((i+1))/${#TEXTBOOKS[@]}] 复制: $name"
    docker cp "$textbook" fitness_daml_rag:"$TEMP_DIR/$filename"
done

echo ""
echo "=========================================="
echo "开始提取知识图谱"
echo "=========================================="
echo ""

# 批量提取
docker exec fitness_daml_rag bash -c "cd /app && python scripts/extract_textbook_knowledge.py \
    --mode batch \
    --input $TEMP_DIR \
    --pattern '*.pdf'"

# 清理临时文件
echo ""
echo "清理临时文件..."
docker exec fitness_daml_rag bash -c "rm -rf $TEMP_DIR"

echo ""
echo "=========================================="
echo "提取完成！"
echo "=========================================="
echo ""
echo "查看提取结果："
echo "  docker exec fitness_daml_rag bash -c 'cd /app && python -c \"from neo4j import GraphDatabase; driver = GraphDatabase.driver(\\\"bolt://neo4j:7687\\\", auth=(\\\"neo4j\\\", \\\"build_body_2024\\\")); result = driver.execute_query(\\\"MATCH (n) WHERE n:Concept OR n:Principle OR n:Mechanism OR n:Guideline OR n:ResearchFinding RETURN labels(n)[0] as NodeType, count(*) as Count ORDER BY Count DESC\\\"); print(result); driver.close()\"'"
echo ""
