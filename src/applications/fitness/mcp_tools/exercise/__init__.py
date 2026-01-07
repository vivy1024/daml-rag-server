"""
Exercise相关MCP工具

包含动作选择、替代品查找等工具
"""

from .intelligent_exercise_selector import (
    IntelligentExerciseSelector,
    IntelligentExerciseSelectorInput,
    IntelligentExerciseSelectorOutput
)

from .exercise_alternative_finder import (
    ExerciseAlternativeFinder,
    ExerciseAlternativeFinderInput,
    ExerciseAlternativeFinderOutput,
    AlternativeExercise,
    AlternativeConstraints
)

__all__ = [
    "IntelligentExerciseSelector",
    "IntelligentExerciseSelectorInput",
    "IntelligentExerciseSelectorOutput",
    "ExerciseAlternativeFinder",
    "ExerciseAlternativeFinderInput",
    "ExerciseAlternativeFinderOutput",
    "AlternativeExercise",
    "AlternativeConstraints"
]
