"""
LLM client for AI decision-making
Supports: Gemini (via official SDK)
"""
import os
import json
import random
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class LLMClient:
    """AI provider client - currently supports Gemini via SDK"""

    def __init__(self):
        """
        Initialize LLM client with Gemini provider
        """
        self.provider = 'gemini'
        self.model = None
        self.api_key = os.getenv('GEMINI_API_KEY')
        
        if self.api_key:
            # Configure the official SDK
            genai.configure(api_key=self.api_key)
            # gemini-1.5-flash is faster/cheaper for decision logic than pro
            self.model = genai.GenerativeModel('gemini-2.5-flash')

    def is_available(self):
        """Check if API key is configured"""
        return self.api_key is not None and self.api_key != ""

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
            print(f"DEBUG: LLM Provider '{self.provider}' not available. Returning fallback.")
            return fallback

        prompt = self.build_prompt(event_data, current_stats)
        print(f"DEBUG: Executing AI Decision with provider: '{self.provider}'")

        try:
            # Official SDK call
            response = self.model.generate_content(prompt)
            # The SDK response object has a .text property
            return self.parse_response_text(response.text)
            
        except Exception as e:
            print(f"LLM API error: {e}")
            return fallback

    def build_prompt(self, event_data, current_stats):
        """Construct prompt for LLM, focusing on the user query"""
        options_text = ""
        for i, opt in enumerate(event_data['options']):
            details = opt.get('details', 'No details provided.')
            # Show 1-based index to AI
            options_text += f"{i + 1}: {opt['text']}\n   Details: {details}\n"

        prompt_content = f"""You are managing a Mars colony. Current stats:
Population: {current_stats['pop']}
Quality of Life: {current_stats['qol']}

EVENT: {event_data['title']}
{event_data['description']}

OPTIONS:
{options_text}

Return ONLY valid JSON (no markdown, no code fences).
Format:
{{
  "choice": 1,
  "reason": "brief explanation"
}}
Choice must be 1, 2, or 3.
"""
        
        if os.getenv('SHOW_LLM_INTERACTION', 'false').lower() == 'true':
            print("\n--- LLM USER PROMPT ---")
            print(prompt_content)
            print("------------------\n")
            
        return prompt_content

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
            choice = int(data.get('choice', 1)) # Default to 1 if missing
            reason = data.get('reason', "No reason provided.")
            
            # Convert 1-based index (1-3) to 0-based index (0-2)
            if 1 <= choice <= 3:
                return {'choice': choice - 1, 'reason': reason}
                
        except (json.JSONDecodeError, ValueError, AttributeError, TypeError) as e:
            print(f"Error parsing LLM response: {e}")
            
            # Use the full text as the reason
            reason = text
            
            # Try to salvage a choice number (1-3)
            choice = random.randint(1, 3)
            for char in text:
                if char.isdigit():
                    num = int(char)
                    if 1 <= num <= 3:
                        choice = num
                        break
            
            return {'choice': choice - 1, 'reason': reason}

        # Fallback
        return {'choice': random.randint(0, 2), 'reason': text if text else "Communication error."}