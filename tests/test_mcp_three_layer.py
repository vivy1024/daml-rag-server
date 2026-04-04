"""Smoke test for MCP Resources + Prompts"""
from src.applications.fitness.mcp_resources import get_resource_registry
from src.applications.fitness.mcp_prompts import get_prompt_registry

def test_resources():
    reg = get_resource_registry()
    resources = reg.list_resources()
    print(f"Resources registered: {len(resources)}")
    for r in resources:
        print(f"  {r['uri']}: {r['name']}")
    
    # Test read
    safety = reg.read_resource("fitness://rules/safety")
    assert safety is not None
    assert "骨盆前倾" in safety
    print(f"  fitness://rules/safety keys: {list(safety.keys())}")
    
    recovery = reg.read_resource("fitness://data/recovery-hours")
    assert recovery["胸大肌"] == 72
    print(f"  fitness://data/recovery-hours: 胸大肌={recovery['胸大肌']}h")
    
    unknown = reg.read_resource("fitness://nonexistent")
    assert unknown is None
    print("Resources OK")

def test_prompts():
    reg = get_prompt_registry()
    prompts = reg.list_prompts()
    print(f"\nPrompts registered: {len(prompts)}")
    for p in prompts:
        print(f"  {p['name']}: {p['description'][:40]}...")
    
    # Test render
    text = reg.get_prompt(
        "training-plan-synthesis",
        user_name="小川",
        fitness_goal="增肌",
        experience_level="中级",
        hard_constraints="左肩禁止过顶推举",
    )
    assert "小川" in text
    assert "增肌" in text
    assert "左肩禁止过顶推举" in text
    print(f"  Rendered length: {len(text)} chars")
    
    # Test fallback prompt
    fallback = reg.get_prompt(
        "harness-policy-deny-fallback",
        deny_reason="缺少安全检查工具",
        template_id="complete_training_plan",
    )
    assert "缺少安全检查工具" in fallback
    print(f"  Fallback prompt length: {len(fallback)} chars")
    
    unknown = reg.get_prompt("nonexistent")
    assert unknown is None
    print("Prompts OK")

if __name__ == "__main__":
    test_resources()
    test_prompts()
    print("\n✅ MCP three-layer smoke test passed!")
