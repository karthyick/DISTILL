"""
Configuration module for DISTILL.

Simplified configuration for the new 3-layer compression architecture.
"""

from typing import Any, Dict, Literal
from dataclasses import dataclass
import copy


@dataclass
class DistillConfig:
    """Configuration for DISTILL compression."""

    # Dictionary encoding
    max_dict_codes: int = 26  # a-z (maximum unique values to encode)
    dict_min_frequency: int = 1  # Min occurrences to include in dictionary
    min_value_length_for_dict: int = 2  # Skip encoding single chars?

    # Equivalence partitioning
    min_equiv_count: int = 2  # Min occurrences for equivalence grouping

    # Tokenizer
    tokenizer: Literal["tiktoken", "approximate"] = "tiktoken"

    # Output options
    fallback_on_increase: bool = True  # Fallback to original if compression increases size
    include_type_hints: bool = False  # Store original types in $ (future use)

    # Validation limits
    max_depth: int = 50
    max_size_mb: int = 100
    max_array_length: int = 100000

    # Type preservation
    preserve_numeric_types: bool = True  # int vs float distinction

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "max_dict_codes": self.max_dict_codes,
            "dict_min_frequency": self.dict_min_frequency,
            "min_value_length_for_dict": self.min_value_length_for_dict,
            "min_equiv_count": self.min_equiv_count,
            "tokenizer": self.tokenizer,
            "fallback_on_increase": self.fallback_on_increase,
            "include_type_hints": self.include_type_hints,
            "max_depth": self.max_depth,
            "max_size_mb": self.max_size_mb,
            "max_array_length": self.max_array_length,
            "preserve_numeric_types": self.preserve_numeric_types,
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "DistillConfig":
        """Create config from dictionary."""
        # Filter out unknown keys
        valid_keys = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in config_dict.items() if k in valid_keys})


# Global configuration instance
_global_config = DistillConfig()


def get_config() -> DistillConfig:
    """Get current global configuration."""
    return _global_config


def configure(**kwargs) -> DistillConfig:
    """
    Update global configuration.

    Args:
        **kwargs: Configuration options to update

    Returns:
        Updated configuration

    Example:
        >>> configure(min_equiv_count=3)
        >>> configure(tokenizer="approximate")
    """
    global _global_config

    for key, value in kwargs.items():
        if hasattr(_global_config, key):
            setattr(_global_config, key, value)
        else:
            raise ValueError(f"Unknown configuration option: {key}")

    return _global_config


def reset_config() -> DistillConfig:
    """Reset configuration to defaults."""
    global _global_config
    _global_config = DistillConfig()
    return _global_config


def with_config(**kwargs):
    """
    Context manager for temporary configuration changes.

    Example:
        >>> with with_config(min_equiv_count=3):
        ...     result = compress(data)
    """
    class ConfigContext:
        def __init__(self, **config_kwargs):
            self.config_kwargs = config_kwargs
            self.original_config = None

        def __enter__(self):
            global _global_config
            self.original_config = copy.deepcopy(_global_config)
            configure(**self.config_kwargs)
            return _global_config

        def __exit__(self, exc_type, exc_val, exc_tb):
            global _global_config
            _global_config = self.original_config
            return False

    return ConfigContext(**kwargs)
