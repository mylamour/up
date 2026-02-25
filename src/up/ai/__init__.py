"""AI engine abstraction layer.

Provides pluggable backends: CliEngine (subprocess) and AgentSdkEngine (in-process).
"""

from up.ai.engine import AIEngine, CliEngine

__all__ = ["AIEngine", "CliEngine"]

try:
    from up.ai.sdk_engine import AgentSdkEngine
    __all__.append("AgentSdkEngine")
except ImportError:
    pass
