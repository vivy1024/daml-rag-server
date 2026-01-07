#!/usr/bin/env python3
"""
Prometheus配置验证脚本
版本: v1.0.0
创建日期: 2025-12-21
"""

import yaml
import sys
from pathlib import Path


def validate_prometheus_config():
    """验证Prometheus配置文件"""
    config_path = Path(__file__).parent.parent / "config" / "prometheus" / "prometheus.yml"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        print("✅ Prometheus配置文件语法正确")
        
        # 检查必要的配置项
        assert 'global' in config, "缺少global配置"
        assert 'rule_files' in config, "缺少rule_files配置"
        assert 'scrape_configs' in config, "缺少scrape_configs配置"
        
        print("✅ Prometheus配置项完整")
        
        # 检查告警规则文件路径
        rule_files = config.get('rule_files', [])
        print(f"📋 告警规则文件: {rule_files}")
        
        return True
        
    except Exception as e:
        print(f"❌ Prometheus配置验证失败: {e}")
        return False


def validate_alert_rules():
    """验证告警规则文件"""
    alerts_path = Path(__file__).parent.parent / "config" / "prometheus" / "alerts" / "workflow_performance.yml"
    
    try:
        with open(alerts_path, 'r', encoding='utf-8') as f:
            rules = yaml.safe_load(f)
        
        print("✅ 告警规则文件语法正确")
        
        # 统计告警规则
        total_rules = 0
        groups = rules.get('groups', [])
        
        for group in groups:
            group_name = group.get('name', 'unknown')
            group_rules = group.get('rules', [])
            rule_count = len(group_rules)
            total_rules += rule_count
            
            print(f"📊 告警组 '{group_name}': {rule_count} 个规则")
            
            # 列出规则名称
            for rule in group_rules:
                alert_name = rule.get('alert', 'unknown')
                severity = rule.get('labels', {}).get('severity', 'unknown')
                print(f"   - {alert_name} ({severity})")
        
        print(f"\n✅ 总计 {total_rules} 个告警规则")
        
        return True
        
    except Exception as e:
        print(f"❌ 告警规则验证失败: {e}")
        return False


def validate_alertmanager_config():
    """验证Alertmanager配置文件"""
    config_path = Path(__file__).parent.parent / "config" / "prometheus" / "alertmanager.yml"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        print("✅ Alertmanager配置文件语法正确")
        
        # 检查必要的配置项
        assert 'route' in config, "缺少route配置"
        assert 'receivers' in config, "缺少receivers配置"
        
        print("✅ Alertmanager配置项完整")
        
        # 统计接收器
        receivers = config.get('receivers', [])
        print(f"📋 接收器数量: {len(receivers)}")
        
        for receiver in receivers:
            receiver_name = receiver.get('name', 'unknown')
            print(f"   - {receiver_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Alertmanager配置验证失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("Prometheus配置验证")
    print("=" * 60)
    print()
    
    success = True
    
    # 验证Prometheus配置
    print("1. 验证Prometheus配置文件")
    print("-" * 60)
    if not validate_prometheus_config():
        success = False
    print()
    
    # 验证告警规则
    print("2. 验证告警规则文件")
    print("-" * 60)
    if not validate_alert_rules():
        success = False
    print()
    
    # 验证Alertmanager配置
    print("3. 验证Alertmanager配置文件")
    print("-" * 60)
    if not validate_alertmanager_config():
        success = False
    print()
    
    # 输出结果
    print("=" * 60)
    if success:
        print("✅ 所有配置验证通过")
        print()
        print("下一步:")
        print("1. 在docker-compose.yml中添加Prometheus和Alertmanager服务")
        print("2. 启动服务: docker-compose up -d prometheus alertmanager")
        print("3. 访问Prometheus: http://localhost:9090")
        print("4. 访问Alertmanager: http://localhost:9093")
        return 0
    else:
        print("❌ 配置验证失败，请检查错误信息")
        return 1


if __name__ == "__main__":
    sys.exit(main())
