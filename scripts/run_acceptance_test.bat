@echo off
REM 运行性能优化验收测试 - 任务20
REM 作者: BUILD_BODY Team
REM 日期: 2025-12-21

echo ========================================
echo 性能优化验收测试 - 任务20
echo ========================================
echo.

REM 检查Docker容器是否运行
echo 检查Docker容器状态...
docker ps | findstr fitness_daml_rag >nul
if errorlevel 1 (
    echo [错误] fitness_daml_rag 容器未运行
    echo 请先启动Docker容器: docker-compose up -d
    pause
    exit /b 1
)

echo [✓] Docker容器运行正常
echo.

REM 运行验收测试
echo 开始运行验收测试...
echo.

docker exec fitness_daml_rag pytest tests/performance/test_task_20_acceptance.py -v --tb=short

if errorlevel 1 (
    echo.
    echo [❌] 验收测试失败
    echo 请查看上述错误信息并进行修复
) else (
    echo.
    echo [✅] 验收测试通过
    echo.
    echo 验收报告已生成:
    echo   - tests/performance/acceptance_report.json
)

echo.
echo ========================================
echo 测试完成
echo ========================================
pause
