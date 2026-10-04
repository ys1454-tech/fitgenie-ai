"""
prompts package — Dedicated prompt templates for FitGenie AI.

Provides modular builders for:
  - Profile extraction:   build_profile_extraction_prompt
  - 7-day plan generation: build_plan_generation_prompt
  - Plan modification:    build_plan_modification_prompt
  - Item substitution:    build_substitution_prompt
"""

from prompts.profile_extraction import build_profile_extraction_prompt
from prompts.plan_generation import build_plan_generation_prompt
from prompts.plan_modification import build_plan_modification_prompt
from prompts.substitution import build_substitution_prompt

__all__ = [
    "build_profile_extraction_prompt",
    "build_plan_generation_prompt",
    "build_plan_modification_prompt",
    "build_substitution_prompt",
]
