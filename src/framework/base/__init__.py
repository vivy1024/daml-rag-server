"""
DAML-RAG Framework Base Module

This module provides the core abstractions for building composable components.
All components in the framework implement the Executable protocol.

Key Classes:
- Executable: Abstract base class for all executable components
- Chain: Composition class for chaining multiple executables
"""

from .executable import Executable, Chain

__all__ = [
    "Executable",
    "Chain",
]
