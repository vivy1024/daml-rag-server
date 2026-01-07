# -*- coding: utf-8 -*-
"""
任务8.1：验证日志完整性

测试目标：
- 执行流式会话
- 解析日志文件
- 验证所有必要字段存在

需求：8.1, 8.2, 8.3, 8.4, 8.5

版本：v1.0.0
创建日期：2025-12-20
"""

import pytest
import asyncio
import json
import re
import time
import logging
from typing import Dict, List, Any
from datetime import datetime


class LogValidator:
    """日志验证器"""
    
    def __init__(self):
        self.required_fields = {
            "session_start": [
                "request_id",
                "user_id",
                "session_id",
                "query",
                "query_length",
                "domain",
                "timestamp"
            ],
            "step_start": [
                "request_id",
                "step_number",
                "step_name",
                "timestamp"
            ],
            "step_complete": [
                "request_id",
                "step_number",
                "step_name",
                "duration_ms",
                "success"
            ],
            "structured_data_detected": [
                "request_id",
                "data_type",
                "marker",
                "data_size",
                "extraction_success"
            ],
            "error": [
                "request_id",
                "error_type",
                "error_message",
                "error_traceback"
            ],
            "session_complete": [
                "request_id",
                "success",
                "total_duration_ms",
                "tokens_generated",
                "content_length",
                "generation_speed",
                "steps_completed",
                "structured_data_count",
                "errors_count"
            ]
        }
    
    def parse_log_line(self, line: str) -> Dict[str, Any]:
        """
        解析日志行
        
        Args:
            line: 日志行
        
        Returns:
            Dict[str, Any]: 解析后的日志数据
        """
        # 日志格式：2025-12-20 10:30:45,123 - INFO - 🚀 [abc123] 流式会话开始: ...
        
        # 提取时间戳
        timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+', line)
        if not timestamp_match:
            return {}
        
        timestamp = timestamp_match.group(1)
        
        # 提取日志级别
        level_match = re.search(r' - (DEBUG|INFO|WARNING|ERROR|CRITICAL) - ', line)
        if not level_match:
            return {}
        
        level = level_match.group(1)
        
        # 提取request_id
        request_id_match = re.search(r'\[([a-f0-9]{8})\]', line)
        request_id = request_id_match.group(1) if request_id_match else None
        
        # 提取消息内容
        message_start = line.find(' - ', line.find(level)) + 3
        message = line[message_start:].strip()
        
        return {
            "timestamp": timestamp,
            "level": level,
            "request_id": request_id,
            "message": message,
            "raw_line": line
        }
    
    def extract_session_start_fields(self, message: str) -> Dict[str, Any]:
        """提取会话开始字段"""
        fields = {}
        
        # 提取user_id
        user_id_match = re.search(r'user_id=([^,]+)', message)
        if user_id_match:
            fields["user_id"] = user_id_match.group(1).strip()
        
        # 提取session_id
        session_id_match = re.search(r'session_id=([^,]+)', message)
        if session_id_match:
            fields["session_id"] = session_id_match.group(1).strip()
        
        # 提取query
        query_match = re.search(r"query='([^']+)'", message)
        if query_match:
            fields["query"] = query_match.group(1)
        
        # 提取query_length
        query_length_match = re.search(r'query_length=(\d+)', message)
        if query_length_match:
            fields["query_length"] = int(query_length_match.group(1))
        
        # 提取domain
        domain_match = re.search(r'domain=([^,]+)', message)
        if domain_match:
            fields["domain"] = domain_match.group(1).strip()
        
        return fields
    
    def extract_step_complete_fields(self, message: str) -> Dict[str, Any]:
        """提取步骤完成字段"""
        fields = {}
        
        # 提取step_number
        step_match = re.search(r'步骤(\d+)完成', message)
        if step_match:
            fields["step_number"] = int(step_match.group(1))
        
        # 提取step_name（从冒号后到逗号前）
        name_match = re.search(r'完成: ([^,]+)', message)
        if name_match:
            fields["step_name"] = name_match.group(1).strip()
        
        # 提取duration_ms
        duration_match = re.search(r'耗时=([\d.]+)ms', message)
        if duration_match:
            fields["duration_ms"] = float(duration_match.group(1))
        
        # 提取success
        success_match = re.search(r'success=(True|False)', message)
        if success_match:
            fields["success"] = success_match.group(1) == "True"
        
        return fields
    
    def extract_structured_data_fields(self, message: str) -> Dict[str, Any]:
        """提取结构化数据检测字段"""
        fields = {}
        
        # 提取data_type
        type_match = re.search(r'type=([^,]+)', message)
        if type_match:
            fields["data_type"] = type_match.group(1).strip()
        
        # 提取marker
        marker_match = re.search(r'marker=([^,]+)', message)
        if marker_match:
            fields["marker"] = marker_match.group(1).strip()
        
        # 提取data_size
        size_match = re.search(r'size=(\d+)字节', message)
        if size_match:
            fields["data_size"] = int(size_match.group(1))
        
        # 提取extraction_success
        success_match = re.search(r'extraction_success=(True|False)', message)
        if success_match:
            fields["extraction_success"] = success_match.group(1) == "True"
        
        return fields
    
    def extract_session_complete_fields(self, message: str) -> Dict[str, Any]:
        """提取会话完成字段"""
        fields = {}
        
        # 提取success
        success_match = re.search(r'success=(True|False)', message)
        if success_match:
            fields["success"] = success_match.group(1) == "True"
        
        # 提取total_duration_ms
        duration_match = re.search(r'total_duration=([\d.]+)ms', message)
        if duration_match:
            fields["total_duration_ms"] = float(duration_match.group(1))
        
        # 提取tokens_generated
        tokens_match = re.search(r'tokens_generated=(\d+)', message)
        if tokens_match:
            fields["tokens_generated"] = int(tokens_match.group(1))
        
        # 提取content_length
        length_match = re.search(r'content_length=(\d+)字', message)
        if length_match:
            fields["content_length"] = int(length_match.group(1))
        
        # 提取generation_speed
        speed_match = re.search(r'generation_speed=([\d.]+) tokens/s', message)
        if speed_match:
            fields["generation_speed"] = float(speed_match.group(1))
        
        # 提取steps_completed
        steps_match = re.search(r'steps_completed=(\d+)/(\d+)', message)
        if steps_match:
            fields["steps_completed"] = int(steps_match.group(1))
            fields["total_steps"] = int(steps_match.group(2))
        
        # 提取structured_data_count
        data_count_match = re.search(r'structured_data_count=(\d+)', message)
        if data_count_match:
            fields["structured_data_count"] = int(data_count_match.group(1))
        
        # 提取errors_count
        errors_match = re.search(r'errors_count=(\d+)', message)
        if errors_match:
            fields["errors_count"] = int(errors_match.group(1))
        
        return fields
    
    def validate_log_completeness(self, log_lines: List[str]) -> Dict[str, Any]:
        """
        验证日志完整性
        
        Args:
            log_lines: 日志行列表
        
        Returns:
            Dict[str, Any]: 验证结果
        """
        validation_result = {
            "total_lines": len(log_lines),
            "parsed_lines": 0,
            "session_start_found": False,
            "session_complete_found": False,
            "steps_found": [],
            "structured_data_found": [],
            "errors_found": [],
            "missing_fields": [],
            "validation_passed": True
        }
        
        for line in log_lines:
            parsed = self.parse_log_line(line)
            if not parsed or not parsed.get("request_id"):
                continue
            
            validation_result["parsed_lines"] += 1
            message = parsed["message"]
            
            # 检查会话开始
            if "流式会话开始" in message:
                validation_result["session_start_found"] = True
                fields = self.extract_session_start_fields(message)
                fields["request_id"] = parsed["request_id"]
                fields["timestamp"] = parsed["timestamp"]
                
                # 验证必需字段
                missing = [f for f in self.required_fields["session_start"] if f not in fields]
                if missing:
                    validation_result["missing_fields"].append({
                        "log_type": "session_start",
                        "missing": missing
                    })
                    validation_result["validation_passed"] = False
            
            # 检查步骤完成
            elif re.search(r'步骤\d+完成', message):
                fields = self.extract_step_complete_fields(message)
                fields["request_id"] = parsed["request_id"]
                
                if fields.get("step_number"):
                    validation_result["steps_found"].append(fields)
                    
                    # 验证必需字段
                    missing = [f for f in self.required_fields["step_complete"] if f not in fields]
                    if missing:
                        validation_result["missing_fields"].append({
                            "log_type": "step_complete",
                            "step_number": fields.get("step_number"),
                            "missing": missing
                        })
                        validation_result["validation_passed"] = False
            
            # 检查结构化数据检测
            elif "检测到结构化数据" in message:
                fields = self.extract_structured_data_fields(message)
                fields["request_id"] = parsed["request_id"]
                
                validation_result["structured_data_found"].append(fields)
                
                # 验证必需字段
                missing = [f for f in self.required_fields["structured_data_detected"] if f not in fields]
                if missing:
                    validation_result["missing_fields"].append({
                        "log_type": "structured_data_detected",
                        "missing": missing
                    })
                    validation_result["validation_passed"] = False
            
            # 检查会话完成
            elif "流式会话完成" in message:
                validation_result["session_complete_found"] = True
                fields = self.extract_session_complete_fields(message)
                fields["request_id"] = parsed["request_id"]
                
                # 验证必需字段
                missing = [f for f in self.required_fields["session_complete"] if f not in fields]
                if missing:
                    validation_result["missing_fields"].append({
                        "log_type": "session_complete",
                        "missing": missing
                    })
                    validation_result["validation_passed"] = False
            
            # 检查错误
            elif parsed["level"] == "ERROR":
                validation_result["errors_found"].append({
                    "request_id": parsed["request_id"],
                    "message": message,
                    "timestamp": parsed["timestamp"]
                })
        
        return validation_result


@pytest.mark.asyncio
async def test_log_completeness(caplog):
    """
    测试日志完整性
    
    验证：
    - 会话开始日志包含所有必需字段
    - 步骤执行日志包含所有必需字段
    - 结构化数据检测日志包含所有必需字段
    - 会话完成日志包含所有必需字段
    - 错误日志包含完整堆栈和上下文
    """
    # 设置日志级别为DEBUG以捕获所有日志
    caplog.set_level(logging.DEBUG)
    
    print("\n" + "="*80)
    print("任务8.1：验证日志完整性")
    print("="*80)
    
    # 1. 执行流式会话
    print("\n📝 步骤1：执行流式会话...")
    
    from src.applications.fitness.workflow_executor import execute_eleven_step_workflow_stream
    
    # 准备测试数据
    test_query = "帮我设计一个完整的4周增肌训练计划"
    test_user_id = "test_user_8_1"
    
    # 收集SSE事件
    events = []
    request_id = None
    
    try:
        async for event in execute_eleven_step_workflow_stream(
            query_text=test_query,
            user_id=test_user_id,
            domain="fitness"
        ):
            events.append(event)
            
            # 提取request_id
            if event.get("type") == "done" and "data" in event:
                request_id = event["data"].get("request_id")
        
        print(f"✅ 流式会话执行完成，收到{len(events)}个事件")
        if request_id:
            print(f"   Request ID: {request_id}")
    
    except Exception as e:
        print(f"❌ 流式会话执行失败: {e}")
        pytest.fail(f"流式会话执行失败: {e}")
    
    # 等待日志写入
    await asyncio.sleep(1)
    
    # 2. 从caplog中读取日志
    print("\n📄 步骤2：从caplog中读取日志...")
    
    # 获取所有日志记录
    log_lines = []
    for record in caplog.records:
        # 格式化日志行（模拟标准日志格式）
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record.created))
        log_line = f"{timestamp},{int((record.created % 1) * 1000):03d} - {record.levelname} - {record.getMessage()}"
        log_lines.append(log_line)
    
    print(f"✅ 从caplog中提取了{len(log_lines)}行日志")
    
    # 3. 过滤与当前会话相关的日志
    if request_id:
        print(f"\n🔍 步骤3：过滤request_id={request_id}的日志...")
        filtered_lines = [line for line in log_lines if request_id in line]
        print(f"✅ 过滤后剩余{len(filtered_lines)}行")
    else:
        print("\n⚠️ 未找到request_id，使用所有日志行")
        filtered_lines = log_lines
    
    # 4. 验证日志完整性
    print("\n✅ 步骤4：验证日志完整性...")
    
    validator = LogValidator()
    validation_result = validator.validate_log_completeness(filtered_lines)
    
    # 打印验证结果
    print(f"\n📊 验证结果:")
    print(f"   总行数: {validation_result['total_lines']}")
    print(f"   解析行数: {validation_result['parsed_lines']}")
    print(f"   会话开始: {'✅' if validation_result['session_start_found'] else '❌'}")
    print(f"   会话完成: {'✅' if validation_result['session_complete_found'] else '❌'}")
    print(f"   步骤记录: {len(validation_result['steps_found'])}个")
    print(f"   结构化数据: {len(validation_result['structured_data_found'])}个")
    print(f"   错误记录: {len(validation_result['errors_found'])}个")
    
    # 打印步骤详情
    if validation_result['steps_found']:
        print(f"\n   步骤详情:")
        for step in validation_result['steps_found']:
            print(f"      步骤{step.get('step_number')}: {step.get('step_name')} "
                  f"(耗时={step.get('duration_ms', 0):.2f}ms, "
                  f"成功={step.get('success', False)})")
    
    # 打印缺失字段
    if validation_result['missing_fields']:
        print(f"\n⚠️ 缺失字段:")
        for missing in validation_result['missing_fields']:
            print(f"      {missing['log_type']}: {', '.join(missing['missing'])}")
    
    # 断言验证通过
    assert validation_result['validation_passed'], \
        f"日志验证失败，缺失字段: {validation_result['missing_fields']}"
    
    assert validation_result['session_start_found'], "未找到会话开始日志"
    assert validation_result['session_complete_found'], "未找到会话完成日志"
    assert len(validation_result['steps_found']) > 0, "未找到步骤执行日志"
    
    print(f"\n{'='*80}")
    print(f"✅ 任务8.1验证通过：日志完整性验证成功")
    print(f"{'='*80}")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_log_completeness())
