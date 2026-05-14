@echo off
REM 批量提取教材知识到 Neo4j（使用 volume mount）
REM 版本: v2.0.0
REM 日期: 2026-02-16
REM 说明: 使用 docker-compose.yml 中配置的 volume mount (./.books:/app/books:ro)

echo ==========================================
echo 教材知识批量提取脚本 v2.0
echo ==========================================
echo.

REM 检查容器是否运行
docker ps | findstr fitness_daml_rag >nul
if errorlevel 1 (
    echo 错误: fitness_daml_rag 容器未运行
    echo 请先启动容器: docker-compose up -d fitness_daml_rag
    pause
    exit /b 1
)

REM 检查 volume mount 是否生效
echo 检查教材目录...
docker exec fitness_daml_rag bash -c "ls /app/books/ >/dev/null 2>&1"
if errorlevel 1 (
    echo.
    echo 警告: /app/books/ 目录不存在
    echo.
    echo 请确认：
    echo   1. docker-compose.yml 中已添加 volume mount: ./.books:/app/books:ro
    echo   2. 已重启容器: docker-compose restart fitness_daml_rag
    echo.
    pause
    exit /b 1
)

echo.
echo 教材文件列表:
docker exec fitness_daml_rag bash -c "ls -lh /app/books/"

echo.
echo ==========================================
echo 开始批量提取知识图谱
echo ==========================================
echo.
echo 这可能需要 30-60 分钟，请耐心等待...
echo.

REM 批量提取（使用容器内的 /app/books/ 路径）
docker exec fitness_daml_rag bash -c "cd /app && python scripts/extract_textbook_knowledge.py --mode batch --input /app/books --pattern '*.pdf'"

echo.
echo ==========================================
echo 提取完成！
echo ==========================================
echo.

REM 查看提取结果
echo 查看提取的节点统计...
docker exec fitness_daml_rag bash -c "cd /app && python -c \"from neo4j import GraphDatabase; driver = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', 'build_body_2024')); result = driver.execute_query('MATCH (n) WHERE n:Concept OR n:Principle OR n:Mechanism OR n:Guideline OR n:ResearchFinding RETURN labels(n)[0] as NodeType, count(*) as Count ORDER BY Count DESC'); records = result.records; print('\\n提取的节点统计:'); [print(f\\\"  {r['NodeType']}: {r['Count']}\\\") for r in records]; driver.close()\""

echo.
echo 查看提取的关系统计...
docker exec fitness_daml_rag bash -c "cd /app && python -c \"from neo4j import GraphDatabase; driver = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', 'build_body_2024')); result = driver.execute_query('MATCH ()-[r]->() WHERE type(r) IN [\\\"EXPLAINS\\\", \\\"BASED_ON\\\", \\\"RECOMMENDS\\\", \\\"SUPPORTS\\\", \\\"APPLIES_TO\\\", \\\"CONTRADICTS\\\"] RETURN type(r) as RelationType, count(*) as Count ORDER BY Count DESC'); records = result.records; print('\\n提取的关系统计:'); [print(f\\\"  {r['RelationType']}: {r['Count']}\\\") for r in records]; driver.close()\""

echo.
echo 在 Neo4j Browser (http://localhost:7474) 中可视化知识图谱
echo.

pause
