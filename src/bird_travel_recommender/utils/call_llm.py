from openai import OpenAI
import os
import logging
from dotenv import load_dotenv
from .prompt_sanitizer import PromptSanitizer

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# Learn more about calling the LLM: https://the-pocket.github.io/PocketFlow/utility_function/llm.html
def call_llm(prompt, sanitize_input=True):
    """
    Call OpenAI LLM with optional input sanitization
    
    Args:
        prompt: The prompt to send to the LLM
        sanitize_input: Whether to sanitize the prompt for security (default: True)
    
    Returns:
        The LLM response
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables. Please set it in your .env file.")
    
    # Optional additional sanitization check
    if sanitize_input and isinstance(prompt, str):
        sanitization_result = PromptSanitizer.sanitize_prompt_input(prompt, input_type='query', strict_mode=False)
        if not sanitization_result.is_safe:
            logger.warning(f"Potentially unsafe prompt detected: {sanitization_result.threats_detected}")
        prompt = sanitization_result.sanitized_text
    
    client = OpenAI(api_key=api_key)
    r = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return r.choices[0].message.content
    
if __name__ == "__main__":
    prompt = "What is the meaning of life?"
    print(call_llm(prompt))
