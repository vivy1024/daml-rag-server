"""Quick smoke test for harness components"""
import asyncio
from src.applications.fitness.harness import ContextPacketBuilder, HarnessTracer

async def test_context_packet():
    builder = ContextPacketBuilder()
    packet = await builder.build(
        user_id='test_user_1',
        message='帮我制定一个增肌计划',
        user_profile={
            'name': '小川', 'age': 25, 'gender': '男',
            'height': 178, 'weight': 72,
            'fitness_goal': '增肌', 'experience_level': '中级',
            'available_equipment': ['哑铃', '杠铃', '卧推凳'],
            'available_time': '60分钟',
        },
        hard_constraints=['左肩旋转袖损伤，禁止过顶推举'],
        long_term_memories=[
            {'content': '喜欢哑铃训练', 'category': 'preference', 'score': 0.85},
            {'content': '常跳过腿部训练', 'category': 'outcome_pattern', 'score': 0.72},
        ],
        conversation_history=[
            {'role': 'user', 'content': '我想增肌'},
            {'role': 'assistant', 'content': '好的，让我为您制定计划'},
        ],
    )
    print(f"Total tokens: {packet.total_tokens}/{packet.total_budget}")
    layers_filled = sum(1 for l in packet.layers.values() if l.content)
    print(f"Layers filled: {layers_filled}/9")
    for name, usage in packet.token_usage_summary().items():
        if usage['used'] > 0:
            print(f"  {name}: {usage['used']}/{usage['budget']} ({usage['utilization_pct']}%)")
    
    hc = packet.get_layer('hard_constraints')
    print(f"hard_constraints compressible: {hc.compressible}")
    print(f"hard_constraints was_compressed: {hc.was_compressed}")
    print(f"hard_constraints content: {hc.content[:100]}")
    
    # Test LLM text output
    llm_text = packet.to_llm_text()
    print(f"\nLLM text length: {len(llm_text)} chars")
    print("ContextPacketBuilder OK")

def test_tracer():
    tracer = HarnessTracer()
    trace = tracer.start_trace("user_1", "complete_training_plan")
    tracer.start_stage("policy")
    tracer.record_policy([{"decision": "allow"}])
    tracer.end_stage("policy")
    tracer.start_stage("context")
    tracer.record_context_packet("1.0", {"total": 500})
    tracer.end_stage("context")
    tracer.record_tool_execution("exercise_selector", 120.5, True)
    tracer.record_verifier({"passed": True, "checks_run": 5})
    result = tracer.end_trace(output_rendered=True)
    print(f"\nTrace ID: {result.trace_id}")
    print(f"Total duration: {result.total_duration_ms}ms")
    print(f"Stages: {list(result.stage_durations_ms.keys())}")
    print(f"Tools executed: {len(result.tools_executed)}")
    print("HarnessTracer OK")

if __name__ == "__main__":
    asyncio.run(test_context_packet())
    test_tracer()
    print("\n✅ All harness smoke tests passed!")
