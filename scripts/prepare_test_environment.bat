@echo off
REM 准备测试环境脚本 (Windows版本)
REM 用于流式工作流综合测试

echo ============================================================
echo 🚀 准备流式工作流综合测试环境
echo ============================================================

REM 步骤1: 验证Docker容器运行状态
echo.
echo 📋 步骤1: 验证Docker容器运行状态
echo ------------------------------------------------------------

docker ps --format "{{.Names}}" | findstr /C:"fitness_daml_rag" >nul
if errorlevel 1 (
    echo    ❌ fitness_daml_rag - 未运行
    goto :error
) else (
    echo    ✅ fitness_daml_rag - 运行中
)

docker ps --format "{{.Names}}" | findstr /C:"fitness_prometheus" >nul
if errorlevel 1 (
    echo    ❌ fitness_prometheus - 未运行
    goto :error
) else (
    echo    ✅ fitness_prometheus - 运行中
)

docker ps --format "{{.Names}}" | findstr /C:"fitness_grafana" >nul
if errorlevel 1 (
    echo    ❌ fitness_grafana - 未运行
    goto :error
) else (
    echo    ✅ fitness_grafana - 运行中
)

REM 步骤2: 清理测试数据
echo.
echo 📋 步骤2: 清理测试数据和历史记录
echo ------------------------------------------------------------
docker exec fitness_daml_rag python scripts/cleanup_test_data.py

REM 步骤3: 验证测试环境
echo.
echo 📋 步骤3: 验证测试环境配置
echo ------------------------------------------------------------
docker exec fitness_daml_rag python scripts/verify_test_environment.py

if errorlevel 1 (
    echo.
    echo ❌ 测试环境验证失败，请检查上述错误
    exit /b 1
)

REM 完成
echo.
echo ============================================================
echo ✅ 测试环境准备完成！
echo ============================================================
echo.
echo 📝 下一步操作：
echo    1. 运行功能测试: docker exec fitness_daml_rag pytest tests/integration/test_streaming_workflow_功能.py -v
echo    2. 运行性能测试: docker exec fitness_daml_rag pytest tests/performance/test_streaming_workflow_性能.py -v
echo    3. 运行完整测试套件: scripts\run_comprehensive_streaming_tests.bat
echo.
exit /b 0

:error
echo.
echo ❌ 部分容器未运行，请先启动所有必需的容器
echo    运行: docker-compose up -d
exit /b 1
