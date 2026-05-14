@echo off
REM 测试单个教材提取（使用最小的 AMJ 论文）
REM 版本: v1.0.0
REM 日期: 2026-02-16

echo ==========================================
echo 测试教材知识提取
echo ==========================================
echo.

REM 使用最小的 PDF 文件进行测试（AMJ-04-107.pdf 只有 135KB）
set TEST_PDF=F:\build_body\.books\AMJ-04-107.pdf
set TEMP_DIR=/app/data/temp_textbooks

echo 创建临时目录...
docker exec fitness_daml_rag bash -c "mkdir -p %TEMP_DIR%"

echo.
echo 复制测试文件到容器...
docker cp "%TEST_PDF%" fitness_daml_rag:%TEMP_DIR%/AMJ-04-107.pdf

echo.
echo ==========================================
echo 开始提取（这可能需要几分钟）
echo ==========================================
echo.

REM 提取单个 PDF
docker exec fitness_daml_rag bash -c "cd /app && python scripts/extract_textbook_knowledge.py --mode pdf --input %TEMP_DIR%/AMJ-04-107.pdf"

echo.
echo ==========================================
echo 提取完成！
echo ==========================================
echo.

REM 查看提取结果
echo 查看提取的节点数量...
docker exec fitness_daml_rag bash -c "cd /app && python -c \"from neo4j import GraphDatabase; driver = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', 'build_body_2024')); result = driver.execute_query('MATCH (n) WHERE n:Concept OR n:Principle OR n:Mechanism OR n:Guideline OR n:ResearchFinding RETURN labels(n)[0] as NodeType, count(*) as Count ORDER BY Count DESC'); records = result.records; print('\\n提取的节点统计:'); [print(f'  {r[\\\"NodeType\\\"]}: {r[\\\"Count\\\"]}') for r in records]; driver.close()\""

echo.
echo 清理临时文件...
docker exec fitness_daml_rag bash -c "rm -rf %TEMP_DIR%"

echo.
echo 测试完成！如果提取成功，可以运行 batch_extract_textbooks.bat 提取所有教材。
echo.

pause
