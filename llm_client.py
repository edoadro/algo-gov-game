"""
LLM client for AI decision-making
Supports multiple providers: Gemini (via official SDK), Ollama, Anthropic (future)
"""
import os
import random
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class LLMClient:
    """AI provider client - currently supports Gemini via SDK"""

    def __init__(self, provider='gemini'):
        """
        Initialize LLM client with specified provider

        Args:
            provider: 'gemini', 'ollama', or 'anthropic'
        """
        self.provider = provider
        self.model = None

        if provider == 'gemini':
            self.api_key = os.getenv('GEMINI_API_KEY')
            if self.api_key:
                # Configure the official SDK
                genai.configure(api_key=self.api_key)
                # gemini-1.5-flash is faster/cheaper for decision logic than pro
                self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Future: elif provider == 'ollama': ...

    def is_available(self):
        """Check if API key is configured"""
        if self.provider == 'gemini':
            return self.api_key is not None and self.api_key != ""
        return False

    def get_ai_decision(self, event_data, current_stats):
        """
        Ask LLM to choose an option for the given event

        Args:
            event_data: Dict with 'title', 'description', 'options'
            current_stats: Dict with 'pop', 'qol'

        Returns:
            dict: {'choice': int, 'reason': str}
        """
        fallback = {'choice': random.randint(0, 2), 'reason': "I made a random choice because my neural link was disrupted."}
        
        if not self.is_available():
            return fallback

        prompt = self.build_prompt(event_data, current_stats)

        try:
            if self.provider == 'gemini':
                # Official SDK call
                response = self.model.generate_content(prompt)
                # The SDK response object has a .text property
                return self.parse_response_text(response.text)
            
            # Future: elif self.provider == 'ollama': ...
            
        except Exception as e:
            print(f"LLM API error: {e}")
            return fallback

    def build_prompt(self, event_data, current_stats):
        """Construct prompt for LLM"""
        options_text = ""
        for i, opt in enumerate(event_data['options']):
            details = opt.get('details', 'No details provided.')
            options_text += f"{i}: {opt['text']}\n   Details: {details}\n"

        prompt = f"""You are managing a Mars colony. Current stats:
Population: {current_stats['pop']}
Quality of Life: {current_stats['qol']}

EVENT: {event_data['title']}
{event_data['description']}

OPTIONS:
{options_text}

Choose the best option (0, 1, or 2) and provide a brief reason.
Respond ONLY with a JSON object in this format:
{{
    "choice": <int>,
    "reason": "<short explanation>"
}}"""
        
        if os.getenv('SHOW_LLM_INTERACTION', 'false').lower() == 'true':
            print("\n--- LLM PROMPT ---")
            print(prompt)
            print("------------------\n")
            
        return prompt

    def parse_response_text(self, text):
        """Extract option and reason from LLM text response"""
        import json
        import re
        
        if os.getenv('SHOW_LLM_INTERACTION', 'false').lower() == 'true':
            print(f"\n--- LLM RESPONSE ---\n{text}\n--------------------\n")

        try:
            # Remove markdown code blocks if present
            clean_text = text.strip()
            if "```json" in clean_text:
                clean_text = clean_text.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_text:
                clean_text = clean_text.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            data = json.loads(clean_text)
            choice = int(data.get('choice', 0))
            reason = data.get('reason', "No reason provided.")
            
            if 0 <= choice <= 2:
                return {'choice': choice, 'reason': reason}
                
        except (json.JSONDecodeError, ValueError, AttributeError, TypeError) as e:
            print(f"Error parsing LLM response: {e}")
            # Try to salvage just a number if JSON fails
            for char in text:
                if char.isdigit():
                    num = int(char)
                    if 0 <= num <= 2:
                        return {'choice': num, 'reason': "I couldn't format my reason properly, but this is my choice."}

        # Fallback if parsing fails completely
        return {'choice': random.randint(0, 2), 'reason': "Communication error. Random fallback initiated."}