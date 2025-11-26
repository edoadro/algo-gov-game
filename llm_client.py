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
            int: Option index (0, 1, or 2)
        """
        if not self.is_available():
            # Fallback: random choice
            return random.randint(0, 2)

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
            # Fallback: random choice
            return random.randint(0, 2)

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

Choose the best option (0, 1, or 2). Respond ONLY with the number."""
        
        if os.getenv('SHOW_LLM_INTERACTION', 'false').lower() == 'true':
            print("\n--- LLM PROMPT ---")
            print(prompt)
            print("------------------\n")
            
        return prompt

    def parse_response_text(self, text):
        """Extract option number from LLM text response"""
        if os.getenv('SHOW_LLM_INTERACTION', 'false').lower() == 'true':
            print(f"\n--- LLM RESPONSE ---\n{text}\n--------------------\n")

        try:
            # Clean string in case of Markdown (e.g., "**1**")
            clean_text = text.strip()
            
            # Extract first digit found
            for char in clean_text:
                if char.isdigit():
                    num = int(char)
                    if 0 <= num <= 2:
                        return num
        except (ValueError, AttributeError, TypeError):
            pass

        # Fallback if parsing fails
        return random.randint(0, 2)