"""RL / trajectory subsystem.

Collects agent interactions as trajectories and exports them in formats
suitable for reinforcement learning and supervised fine-tuning (SFT).
"""

from __future__ import annotations

from argo_brain.rl.trajectory import TrajectoryCollector

__all__ = ["TrajectoryCollector"]
