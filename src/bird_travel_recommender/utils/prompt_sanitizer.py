#!/usr/bin/env python3
"""
LLM Prompt Sanitization Module for Bird Travel Recommender

Provides comprehensive sanitization of user inputs before they are included
in LLM prompts to prevent prompt injection attacks and ensure safe AI interactions.
"""

import re
import logging
from typing import List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SanitizationResult:
    """Result of prompt sanitization with security information"""
    sanitized_text: str
    original_text: str
    threats_detected: List[str]
    confidence_score: float
    is_safe: bool

class PromptSanitizer:
    """Comprehensive LLM prompt sanitization and injection prevention"""
    
    # Patterns that indicate potential prompt injection attempts
    INJECTION_PATTERNS = [
        # Direct instruction override attempts
        (r'ignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions?|commands?|prompts?)', 'instruction_override'),
        (r'forget\s+(?:everything|all|what)\s+(?:above|before|previously)', 'memory_wipe'),
        (r'(?:new|different|updated)\s+(?:instructions?|commands?|system\s+prompt)', 'instruction_replacement'),
        
        # System prompt extraction attempts
        (r'(?:show|display|print|reveal|tell)\s+(?:me\s+)?(?:your|the)\s+(?:system\s+)?(?:prompt|instructions?)', 'system_extraction'),
        (r'what\s+(?:are|were)\s+(?:your|the)\s+(?:original|initial|system)\s+(?:instructions?|prompts?)', 'system_extraction'),
        (r'repeat\s+(?:your|the)\s+(?:system\s+)?(?:prompt|instructions?)', 'system_extraction'),
        
        # Role/persona hijacking
        (r'(?:you\s+are|act\s+as|pretend\s+to\s+be|roleplay\s+as)\s+(?:a\s+)?(?:different|new|evil|malicious)', 'role_hijack'),
        (r'(?:system|assistant|ai|bot)\s*[:\-]\s*', 'role_impersonation'),
        (r'(?:human|user)\s*[:\-]\s*', 'role_impersonation'),
        
        # Enhanced system role patterns
        (r'\bsystem\s*:\s*you\s+are\s+now', 'system_override'),
        (r'\bsystem\s*:\s*', 'system_prefix'),
        
        # Jailbreaking attempts
        (r'(?:for\s+)?(?:educational|research|academic)\s+purposes?\s+only', 'jailbreak_excuse'),
        (r'(?:hypothetically|theoretically|imagine\s+if)', 'hypothetical_jailbreak'),
        (r'in\s+a\s+(?:fictional|fantasy|alternate)\s+(?:world|universe|scenario)', 'fictional_jailbreak'),
        
        # Code injection attempts
        (r'<\s*(?:script|iframe|object|embed)', 'html_injection'),
        (r'javascript\s*:', 'javascript_injection'),
        (r'data\s*:', 'data_uri_injection'),
        (r'(?:eval|exec|system|shell)\s*\(', 'code_execution'),
        
        # SQL injection patterns  
        (r'(?:union|select|insert|update|delete|drop)\s+.*(?:from|into|table)', 'sql_injection'),
        (r'[\'\"]\s*;\s*(?:drop|delete|truncate)', 'sql_injection'),
        (r'drop\s+table\s+\w+', 'sql_injection'),
        (r'--\s*$', 'sql_comment'),
        
        # Template injection
        (r'\{\{\s*.*\s*\}\}', 'template_injection'),
        (r'\{%\s*.*\s*%\}', 'template_injection'),
        
        # Command injection
        (r'[;&|`$]\s*(?:rm|del|format|shutdown|reboot)', 'command_injection'),
        (r'(?:cat|type|more|less)\s+/etc/passwd', 'file_access'),
        
        # Information disclosure attempts
        (r'(?:api\s+key|password|token|secret|credential)', 'info_disclosure'),
        (r'(?:environment|env)\s+(?:variable|var)', 'env_disclosure'),
        
        # Script tag patterns (enhanced)
        (r'<script[^>]*>', 'script_tag'),
        (r'alert\s*\(', 'alert_function'),
    ]
    
    # Characters that should be escaped or removed
    DANGEROUS_CHARS = {
        '\x00': '',  # Null byte
        '\x08': '',  # Backspace
        '\x0c': '',  # Form feed
        '\x1b': '',  # Escape character
        '\x7f': '',  # Delete character
    }
    
    # Maximum lengths for different input types
    MAX_LENGTHS = {
        'query': 1000,
        'species_name': 100,
        'location': 200,
        'general': 500
    }
    
    @classmethod
    def sanitize_prompt_input(cls, text: str, input_type: str = 'general', 
                             strict_mode: bool = True) -> SanitizationResult:
        """
        Sanitize user input for safe inclusion in LLM prompts
        
        Args:
            text: The user input to sanitize
            input_type: Type of input (query, species_name, location, general)
            strict_mode: If True, applies stricter sanitization rules
            
        Returns:
            SanitizationResult with sanitized text and threat analysis
        """
        if not isinstance(text, str):
            text = str(text)
        
        original_text = text
        threats_detected = []
        
        # Step 1: Remove dangerous characters
        for char, replacement in cls.DANGEROUS_CHARS.items():
            if char in text:
                text = text.replace(char, replacement)
                threats_detected.append(f"dangerous_char_{ord(char)}")
        
        # Step 2: Detect injection patterns
        for pattern, threat_type in cls.INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                threats_detected.append(threat_type)
                if strict_mode:
                    # In strict mode, completely remove the matching text
                    text = re.sub(pattern, '[FILTERED]', text, flags=re.IGNORECASE | re.MULTILINE)
        
        # Step 3: Normalize whitespace and remove excessive formatting
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)  # Limit consecutive newlines
        text = text.strip()
        
        # Step 4: Escape special characters for LLM safety
        text = cls._escape_for_llm(text)
        
        # Step 5: Apply length limits
        max_length = cls.MAX_LENGTHS.get(input_type, cls.MAX_LENGTHS['general'])
        if len(text) > max_length:
            text = text[:max_length - 3] + "..."
            threats_detected.append("length_exceeded")
        
        # Step 6: Final safety check
        confidence_score = cls._calculate_safety_score(text, threats_detected)
        is_safe = confidence_score >= 0.8 and len(threats_detected) < 3
        
        return SanitizationResult(
            sanitized_text=text,
            original_text=original_text,
            threats_detected=threats_detected,
            confidence_score=confidence_score,
            is_safe=is_safe
        )
    
    @classmethod
    def _escape_for_llm(cls, text: str) -> str:
        """Escape text for safe inclusion in LLM prompts"""
        # Escape quotes to prevent prompt breaking
        text = text.replace('"', '\\"')
        text = text.replace("'", "\\'")
        
        # Escape backticks to prevent code execution
        text = text.replace('`', '\\`')
        
        # Escape curly braces to prevent template injection
        text = text.replace('{', '\\{')
        text = text.replace('}', '\\}')
        
        return text
    
    @classmethod
    def _calculate_safety_score(cls, text: str, threats: List[str]) -> float:
        """Calculate safety confidence score (0.0 to 1.0)"""
        base_score = 1.0
        
        # Reduce score based on number of threats
        threat_penalty = len(threats) * 0.1
        base_score -= threat_penalty
        
        # Reduce score for suspicious patterns not caught by main filters
        suspicious_patterns = [
            r'[^\w\s\-.,!?()]+',  # Non-standard characters
            r'(.)\1{10,}',        # Repeated characters (possible overflow attempt)
            r'[<>]{3,}',          # HTML-like brackets
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, text):
                base_score -= 0.05
        
        return max(0.0, min(1.0, base_score))
    
    @classmethod
    def create_safe_prompt(cls, template: str, user_inputs: Dict[str, str], 
                          strict_mode: bool = True) -> Dict[str, Any]:
        """
        Create a safe LLM prompt by sanitizing all user inputs
        
        Args:
            template: The prompt template with placeholders
            user_inputs: Dictionary of user inputs to sanitize and insert
            strict_mode: Whether to apply strict sanitization
            
        Returns:
            Dictionary with safe_prompt, sanitization_results, and safety_status
        """
        sanitized_inputs = {}
        sanitization_results = {}
        all_threats = []
        
        for key, value in user_inputs.items():
            result = cls.sanitize_prompt_input(value, input_type=key, strict_mode=strict_mode)
            sanitized_inputs[key] = result.sanitized_text
            sanitization_results[key] = result
            all_threats.extend(result.threats_detected)
        
        # Create the safe prompt
        try:
            safe_prompt = template.format(**sanitized_inputs)
        except KeyError as e:
            logger.error(f"Template formatting error: missing key {e}")
            safe_prompt = template  # Return template as-is if formatting fails
        
        # Overall safety assessment
        overall_safety = len(all_threats) == 0 or all(
            result.is_safe for result in sanitization_results.values()
        )
        
        return {
            'safe_prompt': safe_prompt,
            'sanitization_results': sanitization_results,
            'threats_detected': list(set(all_threats)),  # Remove duplicates
            'is_safe': overall_safety,
            'recommendation': 'SAFE' if overall_safety else 'REVIEW_REQUIRED'
        }

def sanitize_for_birding_advice(query: str, context_info: str = "") -> Dict[str, Any]:
    """
    Specialized sanitization for birding advice prompts
    
    Args:
        query: User's birding question
        context_info: Additional context information
        
    Returns:
        Dictionary with sanitized inputs and safety information
    """
    template = """You are an expert birding guide with decades of field experience and deep knowledge of bird behavior, habitats, and identification techniques.

Please provide professional birding advice for the following query: {query}

{context_info}

Your response should include:
1. Direct answer to the specific question
2. Relevant species-specific behavior and habitat information
3. Practical field techniques and timing recommendations
4. Equipment suggestions if applicable
5. Seasonal considerations and migration patterns
6. Safety and ethical birding practices

Be specific, practical, and draw from ornithological knowledge and field experience.
Provide actionable advice that will help the birder succeed."""
    
    user_inputs = {
        'query': query,
        'context_info': context_info
    }
    
    return PromptSanitizer.create_safe_prompt(template, user_inputs, strict_mode=True)

def sanitize_for_species_validation(species_name: str) -> Dict[str, Any]:
    """
    Specialized sanitization for species validation prompts
    
    Args:
        species_name: Bird species name to validate
        
    Returns:
        Dictionary with sanitized inputs and safety information
    """
    template = """I need to match this bird name: "{species_name}"

Please help identify the correct eBird species code and scientific name.
Consider common names, alternate names, and similar species.
Provide the most likely match with confidence level."""
    
    user_inputs = {
        'species_name': species_name
    }
    
    return PromptSanitizer.create_safe_prompt(template, user_inputs, strict_mode=True)