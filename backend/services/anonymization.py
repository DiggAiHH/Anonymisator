"""
In-memory anonymization service with collision-resistant placeholders.
"""
import re
import hashlib
import secrets
from typing import Dict, Tuple, Set
import logging

logger = logging.getLogger(__name__)


class AnonymizationService:
    """
    In-memory PHI anonymization service.
    
    Generates collision-resistant placeholders and maintains mappings in RAM only.
    """
    
    def __init__(self):
        """Initialize the service with in-memory storage."""
        # Session storage - cleared after each request
        self.current_mappings: Dict[str, str] = {}
        self.used_placeholders: Set[str] = set()
        self.session_salt = secrets.token_hex(16)
    
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
        Anonymize PHI in text using pattern-based detection.
        
        Args:
            text: Original text containing PHI
        
        Returns:
            Tuple of (anonymized_text, mappings_dict)
        """
        # Reset session storage
        self.current_mappings = {}
        self.used_placeholders = set()
        self.session_salt = secrets.token_hex(16)
        
        anonymized_text = text
        
        # Pattern 1: Dates (MM/DD/YYYY, DD/MM/YYYY, YYYY-MM-DD)
        date_pattern = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b'
        for match in re.finditer(date_pattern, text):
            original = match.group(0)
            if original not in self.current_mappings:
                placeholder = self._generate_placeholder(original, "date")
                self.current_mappings[placeholder] = original
                anonymized_text = anonymized_text.replace(original, placeholder, 1)
        
        # Pattern 2: Common IDs (MRN, SSN-like patterns)
        id_pattern = r'\b(?:MRN|ID|SSN)[:\s-]*(\d{3}-\d{2}-\d{4}|\d{9}|\w+\d{4,})\b'
        for match in re.finditer(id_pattern, text, re.IGNORECASE):
            original = match.group(0)
            if original not in self.current_mappings:
                placeholder = self._generate_placeholder(original, "id")
                self.current_mappings[placeholder] = original
                anonymized_text = anonymized_text.replace(original, placeholder, 1)
        
        # Pattern 3: Email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for match in re.finditer(email_pattern, text):
            original = match.group(0)
            if original not in self.current_mappings:
                placeholder = self._generate_placeholder(original, "email")
                self.current_mappings[placeholder] = original
                anonymized_text = anonymized_text.replace(original, placeholder, 1)
        
        # Pattern 4: Phone numbers (improved to handle parentheses and various formats)
        phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
        for match in re.finditer(phone_pattern, text):
            original = match.group(0)
            if original not in self.current_mappings:
                placeholder = self._generate_placeholder(original, "phone")
                self.current_mappings[placeholder] = original
                anonymized_text = anonymized_text.replace(original, placeholder, 1)
        
        # Pattern 5: Simple capitalized names (limited to avoid false positives)
        # Only match common name patterns: "Dr. Name" or "Patient Name Name"
        name_pattern = r'\b(?:Dr\.|Mr\.|Mrs\.|Ms\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'
        for match in re.finditer(name_pattern, text):
            original = match.group(0)
            if original not in self.current_mappings:
                placeholder = self._generate_placeholder(original, "name")
                self.current_mappings[placeholder] = original
                anonymized_text = anonymized_text.replace(original, placeholder, 1)
        
        logger.info(f"Anonymized text with {len(self.current_mappings)} PHI elements")
        return anonymized_text, self.current_mappings
    
    def reidentify(self, text: str, mappings: Dict[str, str]) -> str:
        """
        Re-identify anonymized text using provided mappings.
        
        Args:
            text: Anonymized text with placeholders
            mappings: Dictionary mapping placeholders to original values
        
        Returns:
            Original text with PHI restored
        """
        reidentified_text = text
        
        # Sort by placeholder length (descending) to avoid partial replacements
        sorted_mappings = sorted(mappings.items(), key=lambda x: len(x[0]), reverse=True)
        
        for placeholder, original in sorted_mappings:
            reidentified_text = reidentified_text.replace(placeholder, original)
        
        logger.info(f"Re-identified text using {len(mappings)} mappings")
        return reidentified_text
    
    def clear_session(self):
        """Clear all session data (called after each request)."""
        self.current_mappings.clear()
        self.used_placeholders.clear()
        self.session_salt = secrets.token_hex(16)
