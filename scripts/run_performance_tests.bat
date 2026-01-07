@echo off
REM 性能测试运行脚本 (Windows版本)
REM
REM 用法:
REM   run_performance_tests.bat [test_type]
REM
REM test_type:
REM   all       - 运行所有测试（默认）
REM   e2e       - 只运行端到端性能测试
REM   stress    - 只运行压力测试
REM   quick     - 只运行快速测试
REM
REM 示例:
REM   run_performance_tests.bat all
REM   run_performance_tests.bat e2e
REM   run_performance_tests.bat stress
REM
REM 作者: BUILD_BODY Team
REM 版本: v1.0.0
REM 日期: 2025-12-21

setlocal enabledelayedexpansion

REM 配置
set CONTAINER_NAME=fitness_daml_rag
set TEST_DIR=tests/performance

REM 获取测试类型参数
set TEST_TYPE=%1
if "%TEST_TYPE%"=="" set TEST_TYPE=all

echo.
echo ==========================================
echo   性能测试运行脚本
echo ==========================================
echo.

REM 检查Docker容器状态
echo [INFO] 检查Docker容器状态...
docker ps | findstr %CONTAINER_NAME% >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 容器 %CONTAINER_NAME% 未运行
    echo [INFO] 尝试启动容器...
    docker-compose up -d %CONTAINER_NAME%
    timeout /t 5 /nobreak >nul
)
echo [SUCCESS] 容器 %CONTAINER_NAME% 正在运行
echo.

REM 检查API可用性
echo [INFO] 检查API可用性...
curl -s http://localhost:8001/health >nul 2>&1
if errorlevel 1 (
    echo [ERROR] API不可访问 (http://localhost:8001)
    echo [INFO] 请检查服务日志: docker-compose logs fitness_daml_rag
    exit /b 1
)
echo [SUCCESS] API可访问
echo.

echo ==========================================
echo   开始测试
echo ==========================================
echo.

REM 根据参数运行测试
if "%TEST_TYPE%"=="all" goto run_all
if "%TEST_TYPE%"=="e2e" goto run_e2e
if "%TEST_TYPE%"=="stress" goto run_stress
if "%TEST_TYPE%"=="quick" goto run_quick

echo [ERROR] 未知的测试类型: %TEST_TYPE%
echo.
echo 用法: %0 [test_type]
echo.
echo test_type:
echo   all       - 运行所有测试（默认）
echo   e2e       - 只运行端到端性能测试
echo   stress    - 只运行压力测试
echo   quick     - 只运行快速测试
echo.
exit /b 1

:run_all
echo [INFO] 运行所有性能测试...
echo.
docker exec %CONTAINER_NAME% pytest %TEST_DIR%/ -v
if errorlevel 1 (
    echo [ERROR] 部分测试失败
    set TEST_FAILED=1
) else (
    echo [SUCCESS] 所有测试完成
)
goto show_reports

:run_e2e
echo [INFO] 运行端到端性能测试...
echo.
docker exec %CONTAINER_NAME% pytest %TEST_DIR%/test_e2e_performance.py -v
if errorlevel 1 (
    echo [ERROR] 端到端性能测试失败
    set TEST_FAILED=1
) else (
    echo [SUCCESS] 端到端性能测试完成
)
goto show_reports

:run_stress
echo [INFO] 运行压力测试...
echo.
docker exec %CONTAINER_NAME% pytest %TEST_DIR%/test_stress_test.py -v -m slow
if errorlevel 1 (
    echo [ERROR] 压力测试失败
    set TEST_FAILED=1
) else (
    echo [SUCCESS] 压力测试完成
)
goto show_reports

:run_quick
echo [INFO] 运行快速测试...
echo.
docker exec %CONTAINER_NAME% pytest %TEST_DIR%/ -v -m "not slow"
if errorlevel 1 (
    echo [ERROR] 快速测试失败
    set TEST_FAILED=1
) else (
    echo [SUCCESS] 快速测试完成
)
goto show_reports

:show_reports
echo.
echo ==========================================
echo   测试报告
echo ==========================================
echo.

REM 端到端性能测试报告
docker exec %CONTAINER_NAME% test -f %TEST_DIR%/performance_report.json >nul 2>&1
if not errorlevel 1 (
    echo [SUCCESS] 端到端性能测试报告:
    docker exec %CONTAINER_NAME% cat %TEST_DIR%/performance_report.json
    echo.
)

REM 压力测试报告
docker exec %CONTAINER_NAME% test -f %TEST_DIR%/stress_test_report.json >nul 2>&1
if not errorlevel 1 (
    echo [SUCCESS] 压力测试报告:
    docker exec %CONTAINER_NAME% cat %TEST_DIR%/stress_test_report.json
    echo.
)

echo.
if defined TEST_FAILED (
    echo [ERROR] 测试流程完成，但有失败项
    exit /b 1
) else (
    echo [SUCCESS] 测试流程完成！
)
echo.

endlocal
