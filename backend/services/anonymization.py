"""
In-memory anonymization service with collision-resistant placeholders.

Improvements:
- Position-based replacement to avoid duplicate text issues
- Placeholder validation in re-identification
- Enhanced pattern detection with compiled regex for performance
"""
import re
import hashlib
import secrets
from typing import Dict, Tuple, Set, List, NamedTuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Match:
    """Represents a PHI match with position information."""
    start: int
    end: int
    original: str
    placeholder: str
    category: str


class AnonymizationService:
    """
    In-memory PHI anonymization service.
    
    Generates collision-resistant placeholders and maintains mappings in RAM only.
    Uses position-based replacement to handle duplicate text correctly.
    """
    
    # Pre-compiled regex patterns for better performance
    PATTERNS = {
        'date': re.compile(r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b'),
        'id': re.compile(r'\b(?:MRN|ID|SSN)[:\s-]*(\d{3}-\d{2}-\d{4}|\d{9}|\w+\d{4,})\b', re.IGNORECASE),
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        'phone': re.compile(r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'),
        'name': re.compile(r'\b(?:Dr\.|Mr\.|Mrs\.|Ms\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b')
    }
    
    def __init__(self):
        """Initialize the service with in-memory storage."""
        # Session storage - cleared after each request
        self.current_mappings: Dict[str, str] = {}
        self.used_placeholders: Set[str] = set()
        self.session_salt = secrets.token_hex(16)
        self._anonymization_stats = {'total_phi_elements': 0, 'by_category': {}}
    
    def _generate_placeholder(self, original: str, category: str) -> str:
        """
        Generate a collision-resistant placeholder.
        
        Args:
            original: Original PHI value
            category: Type of PHI (name, date, id, etc.)
        
        Returns:
            Unique placeholder string
        """
        # Create a hash of the original value with session salt for uniqueness
        hash_input = f"{self.session_salt}:{original}:{category}".encode('utf-8')
        hash_digest = hashlib.sha256(hash_input).hexdigest()[:8]
        
        # Generate placeholder with category prefix
        base_placeholder = f"[{category.upper()}_{hash_digest}]"
        
        # Ensure uniqueness
        placeholder = base_placeholder
        counter = 1
        while placeholder in self.used_placeholders:
            placeholder = f"[{category.upper()}_{hash_digest}_{counter}]"
            counter += 1
        
        self.used_placeholders.add(placeholder)
        return placeholder
    
    def anonymize(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Anonymize PHI in text using pattern-based detection with position tracking.
        
        Uses position-based replacement to correctly handle duplicate text.
        Processes all patterns in a single pass, then applies replacements from end to start.
        
        Args:
            text: Original text containing PHI
        
        Returns:
            Tuple of (anonymized_text, mappings_dict)
        """
        # Reset session storage
        self.current_mappings = {}
        self.used_placeholders = set()
        self.session_salt = secrets.token_hex(16)
        self._anonymization_stats = {'total_phi_elements': 0, 'by_category': {}}
        
        # Collect all matches with position information
        all_matches: List[Match] = []
        
        # Process each pattern type
        for category, pattern in self.PATTERNS.items():
            for regex_match in pattern.finditer(text):
                original = regex_match.group(0)
                start = regex_match.start()
                end = regex_match.end()
                
                # Generate placeholder
                placeholder = self._generate_placeholder(original, category)
                self.current_mappings[placeholder] = original
                
                # Track the match with position
                all_matches.append(Match(
                    start=start,
                    end=end,
                    original=original,
                    placeholder=placeholder,
                    category=category
                ))
                
                # Update statistics
                self._anonymization_stats['by_category'][category] = \
                    self._anonymization_stats['by_category'].get(category, 0) + 1
        
        # Sort matches by start position (descending) to replace from end to start
        # This prevents position shifts from affecting subsequent replacements
        all_matches.sort(key=lambda m: m.start, reverse=True)
        
        # Apply replacements from end to start
        anonymized_text = text
        for match in all_matches:
            anonymized_text = (
                anonymized_text[:match.start] + 
                match.placeholder + 
                anonymized_text[match.end:]
            )
        
        self._anonymization_stats['total_phi_elements'] = len(all_matches)
        
        logger.info(
            f"Anonymized text: {len(self.current_mappings)} unique PHI elements, "
            f"Stats: {self._anonymization_stats['by_category']}"
        )
        return anonymized_text, self.current_mappings
    
    def reidentify(self, text: str, mappings: Dict[str, str]) -> str:
        """
        Re-identify anonymized text using provided mappings.
        
        Validates that all expected placeholders are present and warns if any are missing.
        This helps detect if the LLM modified or removed placeholders.
        
        Args:
            text: Anonymized text with placeholders
            mappings: Dictionary mapping placeholders to original values
        
        Returns:
            Original text with PHI restored
        """
        reidentified_text = text
        
        # Validate placeholder presence
        missing_placeholders = []
        for placeholder in mappings.keys():
            if placeholder not in text:
                missing_placeholders.append(placeholder)
        
        if missing_placeholders:
            logger.warning(
                f"Re-identification warning: {len(missing_placeholders)} placeholder(s) "
                f"not found in LLM response. They may have been modified or removed. "
                f"First missing: {missing_placeholders[0]}"
            )
        
        # Sort by placeholder length (descending) to avoid partial replacements
        sorted_mappings = sorted(mappings.items(), key=lambda x: len(x[0]), reverse=True)
        
        for placeholder, original in sorted_mappings:
            reidentified_text = reidentified_text.replace(placeholder, original)
        
        logger.info(
            f"Re-identified text using {len(mappings)} mappings "
            f"({len(missing_placeholders)} placeholders were missing)"
        )
        return reidentified_text
    
    def get_stats(self) -> Dict:
        """Return anonymization statistics for observability."""
        return self._anonymization_stats.copy()
    
    def clear_session(self):
        """Clear all session data (called after each request)."""
        self.current_mappings.clear()
        self.used_placeholders.clear()
        self.session_salt = secrets.token_hex(16)
