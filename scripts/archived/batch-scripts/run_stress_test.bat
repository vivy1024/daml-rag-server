@echo off
REM 压力测试运行脚本 (Windows)
REM 版本: v1.0.0
REM 日期: 2025-12-21

echo ========================================
echo 压力测试运行脚本
echo ========================================
echo.

REM 检查Docker服务
echo 检查Docker服务状态...
docker-compose ps fitness_daml_rag
if %ERRORLEVEL% NEQ 0 (
    echo 错误: fitness_daml_rag容器未运行
    echo 请先启动服务: docker-compose up -d fitness_daml_rag
    pause
    exit /b 1
)

echo.
echo 选择测试模式:
echo 1. 运行完整压力测试 (所有5个场景)
echo 2. 运行场景1: 高并发压力测试
echo 3. 运行场景2: 数据库连接池耗尽
echo 4. 运行场景3: Redis缓存不可用
echo 5. 运行场景4: LLM后端失败
echo 6. 运行场景5: 网络延迟
echo 7. 运行快速验证测试
echo.

set /p choice="请输入选项 (1-7): "

if "%choice%"=="1" (
    echo.
    echo 运行完整压力测试...
    echo 注意: 这将需要较长时间 (约15-20分钟)
    echo.
    docker exec fitness_daml_rag pytest tests/performance/test_task_19_stress_test.py::test_full_stress_test -v -s
) else if "%choice%"=="2" (
    echo.
    echo 运行场景1: 高并发压力测试...
    docker exec fitness_daml_rag pytest tests/performance/test_task_19_stress_test.py::test_scenario_1 -v -s
) else if "%choice%"=="3" (
    echo.
    echo 运行场景2: 数据库连接池耗尽...
    docker exec fitness_daml_rag pytest tests/performance/test_task_19_stress_test.py::test_scenario_2 -v -s
) else if "%choice%"=="4" (
    echo.
    echo 运行场景3: Redis缓存不可用...
    docker exec fitness_daml_rag pytest tests/performance/test_task_19_stress_test.py::test_scenario_3 -v -s
) else if "%choice%"=="5" (
    echo.
    echo 运行场景4: LLM后端失败...
    docker exec fitness_daml_rag pytest tests/performance/test_task_19_stress_test.py::test_scenario_4 -v -s
) else if "%choice%"=="6" (
    echo.
    echo 运行场景5: 网络延迟...
    docker exec fitness_daml_rag pytest tests/performance/test_task_19_stress_test.py::test_scenario_5 -v -s
) else if "%choice%"=="7" (
    echo.
    echo 运行快速验证测试...
    docker exec fitness_daml_rag pytest tests/performance/test_quick_validation.py -v -s
) else (
    echo.
    echo 无效的选项
    pause
    exit /b 1
)

echo.
echo ========================================
echo 测试完成
echo ========================================
echo.
echo 查看测试报告:
echo   tests/performance/stress_test_report.json
echo.
echo 查看详细文档:
echo   docs/07-测试报告/02-压力测试报告.md
echo.

pause
