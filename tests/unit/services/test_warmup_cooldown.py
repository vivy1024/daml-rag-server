"""
热身放松动作配置测试

测试WarmupCooldownSelector的功能
"""
import pytest
from src.applications.fitness.services.warmup_cooldown_exercises import (
    WarmupCooldownSelector,
    TrainingFocus,
    GENERAL_WARMUP_CARDIO,
    UPPER_BODY_WARMUP,
    LOWER_BODY_WARMUP,
    CHEST_COOLDOWN,
    LEGS_COOLDOWN,
    WarmupExercise,
    CooldownExercise,
)


class TestWarmupCooldownConfig:
    """测试热身放松动作配置"""
    
    def test_general_warmup_cardio_not_empty(self):
        """测试通用有氧热身动作不为空"""
        assert len(GENERAL_WARMUP_CARDIO) > 0
        
    def test_upper_body_warmup_not_empty(self):
        """测试上肢热身动作不为空"""
        assert len(UPPER_BODY_WARMUP) > 0
        
    def test_lower_body_warmup_not_empty(self):
        """测试下肢热身动作不为空"""
        assert len(LOWER_BODY_WARMUP) > 0
        
    def test_warmup_exercise_has_required_fields(self):
        """测试热身动作有必需字段"""
        for ex in GENERAL_WARMUP_CARDIO:
            assert isinstance(ex, WarmupExercise)
            assert ex.exercise_id > 0
            assert len(ex.name_zh) > 0
            assert ex.duration_seconds > 0
            
    def test_cooldown_exercise_has_required_fields(self):
        """测试放松动作有必需字段"""
        for ex in CHEST_COOLDOWN:
            assert isinstance(ex, CooldownExercise)
            assert ex.exercise_id > 0
            assert len(ex.name_zh) > 0
            assert ex.duration_seconds > 0


class TestWarmupCooldownSelector:
    """测试热身放松动作选择器"""
    
    def test_get_warmup_exercises_returns_list(self):
        """测试获取热身动作返回列表"""
        warmup = WarmupCooldownSelector.get_warmup_exercises(
            training_focus=TrainingFocus.CHEST,
            duration_minutes=10
        )
        assert isinstance(warmup, list)
        assert len(warmup) > 0
        
    def test_get_warmup_exercises_has_cardio(self):
        """测试热身动作包含有氧"""
        warmup = WarmupCooldownSelector.get_warmup_exercises(
            training_focus=TrainingFocus.UPPER_BODY,
            duration_minutes=10,
            include_cardio=True
        )
        cardio_exercises = [ex for ex in warmup if ex["category"] == "有氧热身"]
        assert len(cardio_exercises) > 0
        
    def test_get_warmup_exercises_no_cardio(self):
        """测试热身动作不包含有氧"""
        warmup = WarmupCooldownSelector.get_warmup_exercises(
            training_focus=TrainingFocus.UPPER_BODY,
            duration_minutes=10,
            include_cardio=False
        )
        cardio_exercises = [ex for ex in warmup if ex["category"] == "有氧热身"]
        assert len(cardio_exercises) == 0
        
    def test_get_cooldown_exercises_returns_list(self):
        """测试获取放松动作返回列表"""
        cooldown = WarmupCooldownSelector.get_cooldown_exercises(
            training_focus=TrainingFocus.LEGS,
            duration_minutes=10
        )
        assert isinstance(cooldown, list)
        assert len(cooldown) > 0
        
    def test_warmup_exercise_format(self):
        """测试热身动作格式正确"""
        warmup = WarmupCooldownSelector.get_warmup_exercises(
            training_focus=TrainingFocus.CHEST,
            duration_minutes=5
        )
        for ex in warmup:
            assert "exercise_id" in ex
            assert "name_zh" in ex
            assert "category" in ex
            assert "type" in ex
            assert ex["type"] == "warmup"
            assert "duration_seconds" in ex
            
    def test_cooldown_exercise_format(self):
        """测试放松动作格式正确"""
        cooldown = WarmupCooldownSelector.get_cooldown_exercises(
            training_focus=TrainingFocus.BACK,
            duration_minutes=5
        )
        for ex in cooldown:
            assert "exercise_id" in ex
            assert "name_zh" in ex
            assert "category" in ex
            assert "type" in ex
            assert ex["type"] == "cooldown"
            assert "duration_seconds" in ex


class TestTrainingFocusDetermination:
    """测试训练重点判断"""
    
    def test_chest_focus(self):
        """测试胸部训练重点"""
        focus = WarmupCooldownSelector.determine_training_focus(
            ["胸大肌", "三角肌", "肱三头肌"],
            "push_pull_legs"
        )
        assert focus == TrainingFocus.CHEST
        
    def test_back_focus(self):
        """测试背部训练重点"""
        focus = WarmupCooldownSelector.determine_training_focus(
            ["背阔肌", "肱二头肌"],
            "push_pull_legs"
        )
        assert focus == TrainingFocus.BACK
        
    def test_lower_body_focus(self):
        """测试下肢训练重点"""
        focus = WarmupCooldownSelector.determine_training_focus(
            ["股四头肌", "腘绳肌", "臀大肌"],
            "upper_lower"
        )
        assert focus == TrainingFocus.LOWER_BODY
        
    def test_full_body_focus(self):
        """测试全身训练重点"""
        focus = WarmupCooldownSelector.determine_training_focus(
            ["胸大肌", "背阔肌", "股四头肌"],
            "full_body"
        )
        assert focus == TrainingFocus.FULL_BODY
        
    def test_core_focus(self):
        """测试核心训练重点"""
        focus = WarmupCooldownSelector.determine_training_focus(
            ["腹直肌", "腹斜肌", "下背部"],
            "bro_split"
        )
        assert focus == TrainingFocus.CORE


class TestAllTrainingFocusHaveExercises:
    """测试所有训练重点都有对应的热身放松动作"""
    
    @pytest.mark.parametrize("focus", list(TrainingFocus))
    def test_warmup_mapping_exists(self, focus):
        """测试每个训练重点都有热身动作映射"""
        warmup = WarmupCooldownSelector.get_warmup_exercises(
            training_focus=focus,
            duration_minutes=10
        )
        assert len(warmup) > 0, f"训练重点 {focus.value} 没有热身动作"
        
    @pytest.mark.parametrize("focus", list(TrainingFocus))
    def test_cooldown_mapping_exists(self, focus):
        """测试每个训练重点都有放松动作映射"""
        cooldown = WarmupCooldownSelector.get_cooldown_exercises(
            training_focus=focus,
            duration_minutes=10
        )
        assert len(cooldown) > 0, f"训练重点 {focus.value} 没有放松动作"
