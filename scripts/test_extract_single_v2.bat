@echo off
REM 测试单个教材提取（使用 volume mount）
REM 版本: v2.0.0
REM 日期: 2026-02-16

echo ==========================================
echo 测试教材知识提取 v2.0
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
echo 使用最小的 PDF 文件进行测试（AMJ-04-107.pdf）
echo.

REM 检查测试文件是否存在
docker exec fitness_daml_rag bash -c "ls /app/books/AMJ-04-107.pdf >/dev/null 2>&1"
if errorlevel 1 (
    echo 错误: /app/books/AMJ-04-107.pdf 不存在
    echo.
    echo 可用的教材文件:
    docker exec fitness_daml_rag bash -c "ls -lh /app/books/"
    pause
    exit /b 1
)

echo ==========================================
echo 开始提取（这可能需要 2-5 分钟）
echo ==========================================
echo.

REM 提取单个 PDF
docker exec fitness_daml_rag bash -c "cd /app && python scripts/extract_textbook_knowledge.py --mode pdf --input /app/books/AMJ-04-107.pdf"

echo.
echo ==========================================
echo 提取完成！
echo ==========================================
echo.

REM 查看提取结果
echo 查看提取的节点统计...
docker exec fitness_daml_rag bash -c "cd /app && python -c \"from neo4j import GraphDatabase; driver = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', 'build_body_2024')); result = driver.execute_query('MATCH (n) WHERE n:Concept OR n:Principle OR n:Mechanism OR n:Guideline OR n:ResearchFinding RETURN labels(n)[0] as NodeType, count(*) as Count ORDER BY Count DESC'); records = result.records; print('\\n提取的节点统计:'); [print(f\\\"  {r['NodeType']}: {r['Count']}\\\") for r in records]; driver.close()\""

echo.
echo 测试完成！如果提取成功，可以运行 batch_extract_textbooks_v2.bat 提取所有教材。
echo.

pause
