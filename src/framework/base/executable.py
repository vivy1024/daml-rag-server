"""
Executable Protocol and Chain Class

This module defines the core Executable protocol that all framework components
implement. Similar to LangChain's Runnable interface, it provides a unified
way to execute, stream, and compose components.

Requirements: 8.1, 8.5, 8.6
"""

from abc import ABC, abstractmethod
from typing import (
    Dict,
    Any,
    Optional,
    AsyncIterator,
    List,
    TypeVar,
    Generic,
    Union,
)
import asyncio
from dataclasses import dataclass, field


# Type variables for generic typing
InputType = TypeVar("InputType", bound=Dict[str, Any])
OutputType = TypeVar("OutputType", bound=Dict[str, Any])


@dataclass
class ExecutionConfig:
    """
    Configuration for execution context.
    
    Attributes:
        timeout: Maximum execution time in seconds
        max_retries: Maximum number of retry attempts
        metadata: Additional metadata for the execution
    """
    timeout: Optional[float] = None
    max_retries: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class Executable(ABC):
    """
    Abstract base class for all executable components.
    
    This protocol defines the interface that all framework components must
    implement. It supports both synchronous and asynchronous execution,
    streaming output, and composition via the pipe operator.
    
    Similar to LangChain's Runnable interface, this provides a unified
    way to build composable AI pipelines.
    
    Example:
        ```python
        class MyRetriever(Executable):
            async def execute(self, input, config=None):
                # Retrieve documents
                return {"documents": [...]}
        
        class MyGenerator(Executable):
            async def execute(self, input, config=None):
                # Generate response
                return {"response": "..."}
        
        # Compose using pipe operator
        pipeline = MyRetriever() | MyGenerator()
        result = await pipeline.execute({"query": "..."})
        ```
    """
    
    @property
    def name(self) -> str:
        """Return the name of this executable."""
        return self.__class__.__name__
    
    @abstractmethod
    async def execute(
        self,
        input: Dict[str, Any],
        config: Optional[ExecutionConfig] = None
    ) -> Dict[str, Any]:
        """
        Execute the component with the given input.
        
        Args:
            input: Input dictionary containing the data to process
            config: Optional execution configuration
            
        Returns:
            Output dictionary containing the results
            
        Raises:
            ExecutionError: If execution fails
        """
        pass
    
    async def stream(
        self,
        input: Dict[str, Any],
        config: Optional[ExecutionConfig] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream the execution output.
        
        Default implementation yields the complete result as a single chunk.
        Override this method to provide true streaming behavior.
        
        Args:
            input: Input dictionary containing the data to process
            config: Optional execution configuration
            
        Yields:
            Output chunks as dictionaries
        """
        result = await self.execute(input, config)
        yield result
    
    async def batch(
        self,
        inputs: List[Dict[str, Any]],
        config: Optional[ExecutionConfig] = None,
        max_concurrency: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Execute the component on multiple inputs concurrently.
        
        Args:
            inputs: List of input dictionaries
            config: Optional execution configuration
            max_concurrency: Maximum number of concurrent executions
            
        Returns:
            List of output dictionaries in the same order as inputs
        """
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def execute_with_semaphore(inp: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                return await self.execute(inp, config)
        
        tasks = [execute_with_semaphore(inp) for inp in inputs]
        return await asyncio.gather(*tasks)
    
    def __or__(self, other: "Executable") -> "Chain":
        """
        Compose this executable with another using the pipe operator.
        
        Args:
            other: The executable to chain after this one
            
        Returns:
            A Chain containing both executables
            
        Example:
            ```python
            pipeline = retriever | generator | formatter
            ```
        """
        if isinstance(other, Chain):
            return Chain([self] + other.executables)
        return Chain([self, other])
    
    def __ror__(self, other: "Executable") -> "Chain":
        """
        Support reverse pipe operator for composition.
        
        Args:
            other: The executable to chain before this one
            
        Returns:
            A Chain containing both executables
        """
        if isinstance(other, Chain):
            return Chain(other.executables + [self])
        return Chain([other, self])


class Chain(Executable):
    """
    A composition of multiple executables that execute in sequence.
    
    The output of each executable is passed as input to the next one.
    This enables building complex pipelines from simple components.
    """
    
    def __init__(self, executables: List[Executable]):
        """
        Initialize the chain with a list of executables.
        
        Args:
            executables: List of executables to chain together
            
        Raises:
            ValueError: If executables list is empty
        """
        if not executables:
            raise ValueError("Chain must contain at least one executable")
        self._executables = executables
    
    @property
    def executables(self) -> List[Executable]:
        """Return the list of executables in this chain."""
        return self._executables
    
    @property
    def name(self) -> str:
        """Return a descriptive name for this chain."""
        names = [e.name for e in self._executables]
        return f"Chain({' | '.join(names)})"
    
    @property
    def first(self) -> Executable:
        """Return the first executable in the chain."""
        return self._executables[0]
    
    @property
    def last(self) -> Executable:
        """Return the last executable in the chain."""
        return self._executables[-1]
    
    def __len__(self) -> int:
        """Return the number of executables in the chain."""
        return len(self._executables)
    
    async def execute(
        self,
        input: Dict[str, Any],
        config: Optional[ExecutionConfig] = None
    ) -> Dict[str, Any]:
        """
        Execute all components in sequence.
        """
        current_output = input
        for executable in self._executables:
            current_output = await executable.execute(current_output, config)
        return current_output
    
    async def stream(
        self,
        input: Dict[str, Any],
        config: Optional[ExecutionConfig] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream execution through the chain.
        """
        # Execute all but the last component
        current_output = input
        for executable in self._executables[:-1]:
            current_output = await executable.execute(current_output, config)
        
        # Stream the last component
        async for chunk in self._executables[-1].stream(current_output, config):
            yield chunk
    
    def __or__(self, other: "Executable") -> "Chain":
        """Extend this chain with another executable."""
        if isinstance(other, Chain):
            return Chain(self._executables + other.executables)
        return Chain(self._executables + [other])
    
    def __ror__(self, other: "Executable") -> "Chain":
        """Prepend an executable to this chain."""
        if isinstance(other, Chain):
            return Chain(other.executables + self._executables)
        return Chain([other] + self._executables)


class PassthroughExecutable(Executable):
    """A simple executable that passes input through unchanged."""
    
    async def execute(
        self,
        input: Dict[str, Any],
        config: Optional[ExecutionConfig] = None
    ) -> Dict[str, Any]:
        """Return the input unchanged."""
        return input


class TransformExecutable(Executable):
    """An executable that applies a transformation function to input."""
    
    def __init__(
        self,
        transform_fn,
        name: Optional[str] = None
    ):
        """
        Initialize with a transformation function.
        
        Args:
            transform_fn: Function or coroutine that transforms input to output
            name: Optional name for this transformer
        """
        self._transform_fn = transform_fn
        self._name = name
    
    @property
    def name(self) -> str:
        """Return the name of this transformer."""
        return self._name or f"Transform({self._transform_fn.__name__})"
    
    async def execute(
        self,
        input: Dict[str, Any],
        config: Optional[ExecutionConfig] = None
    ) -> Dict[str, Any]:
        """Apply the transformation function to the input."""
        result = self._transform_fn(input)
        # Handle both sync and async transform functions
        if asyncio.iscoroutine(result):
            return await result
        return result
