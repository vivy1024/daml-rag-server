@echo off
REM 批量提取教材知识到 Neo4j (Windows版本)
REM 版本: v1.0.0
REM 日期: 2026-02-16

echo ==========================================
echo 教材知识批量提取脚本
echo ==========================================
echo.

REM 教材文件列表（宿主机路径）
set TEXTBOOK1=F:\build_body\.books\Open-Textbook-of-Exercise-Physiology-1756071395.pdf
set TEXTBOOK2=F:\build_body\.books\foundationsoffitnessprogramming_201508.pdf
set TEXTBOOK3=F:\build_body\.books\Introduction_to_Sports_Biomechanics.pdf
set TEXTBOOK4=F:\build_body\.books\AMJ-04-107.pdf

REM 临时目录（容器内）
set TEMP_DIR=/app/data/temp_textbooks

REM 创建临时目录
echo 创建临时目录...
docker exec fitness_daml_rag bash -c "mkdir -p %TEMP_DIR%"

REM 复制教材到容器
echo.
echo 复制教材文件到容器...
echo   [1/4] 复制: 运动生理学开放教材
docker cp "%TEXTBOOK1%" fitness_daml_rag:%TEMP_DIR%/Open-Textbook-of-Exercise-Physiology-1756071395.pdf

echo   [2/4] 复制: NSCA Foundations of Fitness Programming
docker cp "%TEXTBOOK2%" fitness_daml_rag:%TEMP_DIR%/foundationsoffitnessprogramming_201508.pdf

echo   [3/4] 复制: 运动生物力学导论
docker cp "%TEXTBOOK3%" fitness_daml_rag:%TEMP_DIR%/Introduction_to_Sports_Biomechanics.pdf

echo   [4/4] 复制: AMJ论文
docker cp "%TEXTBOOK4%" fitness_daml_rag:%TEMP_DIR%/AMJ-04-107.pdf

echo.
echo ==========================================
echo 开始提取知识图谱
echo ==========================================
echo.

REM 批量提取
docker exec fitness_daml_rag bash -c "cd /app && python scripts/extract_textbook_knowledge.py --mode batch --input %TEMP_DIR% --pattern '*.pdf'"

REM 清理临时文件
echo.
echo 清理临时文件...
docker exec fitness_daml_rag bash -c "rm -rf %TEMP_DIR%"

echo.
echo ==========================================
echo 提取完成！
echo ==========================================
echo.
echo 查看提取结果（在 Neo4j Browser 中运行）：
echo   MATCH (n) WHERE n:Concept OR n:Principle OR n:Mechanism OR n:Guideline OR n:ResearchFinding
echo   RETURN labels(n)[0] as NodeType, count(*) as Count ORDER BY Count DESC
echo.

pause
