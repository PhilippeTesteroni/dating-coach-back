import re
import random
import logging
from typing import Dict, Any, Optional

from app.client import service_client

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Builds system prompts for conversations.
    
    Character modes: template + character.base_prompt + scenario + difficulty
    Coach modes: hitch.base_prompt + scenario
    """
    
    @staticmethod
    def calculate_orientation(user_gender: str, user_preference: str) -> str:
        """
        Calculate model's sexual orientation based on user preferences.
        
        Logic:
        - user=male + pref=female → heterosexual (model is female attracted to males)
        - user=female + pref=male → heterosexual (model is male attracted to females)
        - user=male + pref=male → homosexual
        - user=female + pref=female → homosexual
        - pref=all → bisexual
        """
        if user_preference == "all":
            return "bisexual"
        
        if user_gender == user_preference:
            return "homosexual"
        
        return "heterosexual"
    
    @staticmethod
    def generate_model_age(age_min: int, age_max: int) -> int:
        """Generate random age within user's preferred range."""
        return random.randint(age_min, age_max)
    
    @staticmethod
    def replace_placeholders(template: str, variables: Dict[str, Any]) -> str:
        """Replace {{variable}} placeholders in template."""
        def replacer(match):
            var_name = match.group(1)
            value = variables.get(var_name, "")
            return str(value) if value else ""
        
        return re.sub(r'\{\{(\w+)\}\}', replacer, template)

    @classmethod
    async def build_character_prompt(
        cls,
        character: Dict[str, Any],
        scenario: Dict[str, Any],
        user_gender: str,
        user_preference: str,
        model_age: int,
        language: str = "ru",
        difficulty_level: Optional[int] = None
    ) -> str:
        """
        Build system prompt for character mode.
        
        Components:
        1. Base template (character_system.txt)
        2. Character's base_prompt
        3. Scenario prompt
        4. Difficulty modifier (if applicable)
        """
        # Load template
        template = await service_client.get_template("character_system")
        
        # Calculate orientation
        model_orientation = cls.calculate_orientation(user_gender, user_preference)
        
        # Get difficulty prompt if needed
        difficulty_prompt = ""
        if difficulty_level and scenario.get("difficulty_levels"):
            for level in scenario["difficulty_levels"]:
                if level["level"] == difficulty_level:
                    difficulty_prompt = level.get("modifier_prompt", "")
                    break
        
        # Build training scenario text
        training_scenario = scenario.get("scenario_prompt", "")
        if difficulty_prompt:
            training_scenario += f"\n\n{difficulty_prompt}"
        
        # Prepare variables
        variables = {
            "user_gender": user_gender,
            "user_preference_gender": user_preference,
            "character_prompt": character.get("base_prompt", ""),
            "model_age": model_age,
            "model_orientation": model_orientation,
            "language": language,
            "training_scenario": training_scenario
        }
        
        # Build final prompt
        system_prompt = cls.replace_placeholders(template, variables)
        
        logger.info(f"✅ Built character prompt: char={character.get('id')}, mode={scenario.get('mode_id')}")
        
        return system_prompt

    @classmethod
    async def build_greeting_prompt(
        cls,
        character: Dict[str, Any],
        scenario: Dict[str, Any],
        language: str = "en",
        user_gender: Optional[str] = None,
        user_age_min: Optional[int] = None,
        user_age_max: Optional[int] = None,
    ) -> tuple[str, str]:
        """
        Build system + user prompt specifically for greeting generation.

        Keeps greeting separate from the main conversation prompt —
        lighter, character-voice-focused, user-context-aware.

        Returns (system_prompt, user_message).
        """
        is_coach = character.get("type") == "coach"

        # --- System prompt ---
        base_prompt = character.get("base_prompt", "")
        greeting_style = character.get("greeting_style", "")

        greeting_style_block = (
            f"GREETING STYLE:\n{greeting_style}" if greeting_style else ""
        )

        language_instruction = (
            "LANGUAGE: Respond in English by default. "
            "If the user writes in another language, switch immediately."
        )

        system_parts = [p for p in [base_prompt, greeting_style_block, language_instruction] if p]
        system_prompt = "\n\n".join(system_parts)

        # --- User message (task + user context) ---
        greeting_instruction = scenario.get(
            "greeting_instruction",
            "Open the conversation naturally. One or two sentences max."
        )

        context_parts = []
        if user_gender:
            context_parts.append(f"user gender: {user_gender}")
        if user_age_min is not None and user_age_max is not None:
            context_parts.append(f"user age range: {user_age_min}–{user_age_max}")

        user_context = f"Context: {', '.join(context_parts)}." if context_parts else ""

        user_message_parts = [p for p in [user_context, greeting_instruction] if p]
        user_message = "\n".join(user_message_parts)

        logger.info(
            f"✅ Built greeting prompt: char={character.get('id')}, "
            f"submode={scenario.get('id')}, lang={language}"
        )

        return system_prompt, user_message
        cls,
        coach_character: Dict[str, Any],
        scenario: Dict[str, Any],
        language: str = "ru"
    ) -> str:
        """
        Build system prompt for coach mode.
        
        Components:
        1. Hitch's base_prompt
        2. Scenario prompt
        """
        base_prompt = coach_character.get("base_prompt", "")
        scenario_prompt = scenario.get("scenario_prompt", "")

        language_instruction = (
            "LANGUAGE: Respond in English by default. "
            "If the user writes in another language, switch to that language immediately "
            "and maintain it throughout the conversation."
        )

        system_prompt = f"{base_prompt}\n\n{scenario_prompt}\n\n{language_instruction}"
        
        logger.info(f"✅ Built coach prompt: mode={scenario.get('mode_id')}")
        
        return system_prompt
