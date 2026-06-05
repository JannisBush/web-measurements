"""
QuestionLoader class for loading question metadata and options.

This module provides functionality to load question text, options, and metadata
from the survey schema and custom options files.
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path


class QuestionLoader:
    """Loads question metadata and options for display."""
    
    def __init__(self, schema_path: str = "data/surveyjson.json", 
                 custom_options_path: str = "data/custom-options.json"):
        """
        Initialize the QuestionLoader.
        
        Args:
            schema_path: Path to the survey schema JSON file
            custom_options_path: Path to the custom options JSON file
        """
        self.schema_path = Path(schema_path)
        self.custom_options_path = Path(custom_options_path)
        self._schema_cache = None
        self._custom_options_cache = None
    
    def get_question_text(self, question_id: str) -> Optional[str]:
        """
        Get question text from surveyjson.json.
        
        Args:
            question_id: ID of the question
            
        Returns:
            Question text or None if not found
        """
        schema = self._load_schema()
        question_element = self._find_question_element(question_id, schema)
        
        if question_element:
            return question_element.get('title', '')
        
        return None
    
    def get_question_options(self, question_id: str) -> List[Dict[str, str]]:
        """
        Get available options for a question, including custom options.
        
        Args:
            question_id: ID of the question
            
        Returns:
            List of option dictionaries with 'value' and 'text' keys
        """
        options = []
        
        # Get options from schema
        schema = self._load_schema()
        question_element = self._find_question_element(question_id, schema)
        
        if question_element:
            # Check for static choices
            if 'choices' in question_element:
                for choice in question_element['choices']:
                    if isinstance(choice, dict):
                        options.append({
                            'value': choice.get('value', ''),
                            'text': choice.get('text', choice.get('value', ''))
                        })
                    else:
                        options.append({
                            'value': str(choice),
                            'text': str(choice)
                        })
        
        # Get custom options
        custom_options = self._load_custom_options()
        if question_id in custom_options:
            for option in custom_options[question_id]:
                if isinstance(option, dict):
                    options.append({
                        'value': option.get('value', ''),
                        'text': option.get('text', option.get('value', ''))
                    })
                else:
                    options.append({
                        'value': str(option),
                        'text': str(option)
                    })
        
        return options
    
    def get_question_type(self, question_id: str) -> Optional[str]:
        """
        Get question type (checkbox, radiogroup, etc.).
        
        Args:
            question_id: ID of the question
            
        Returns:
            Question type or None if not found
        """
        schema = self._load_schema()
        question_element = self._find_question_element(question_id, schema)
        
        if question_element:
            return question_element.get('type', '')
        
        return None
    
    def get_question_metadata(self, question_id: str) -> Dict[str, Any]:
        """
        Get complete question metadata.
        
        Args:
            question_id: ID of the question
            
        Returns:
            Dictionary containing question metadata
        """
        schema = self._load_schema()
        question_element = self._find_question_element(question_id, schema)
        
        if not question_element:
            return {}
        
        metadata = {
            'question_id': question_id,
            'title': question_element.get('title', ''),
            'type': question_element.get('type', ''),
            'required': question_element.get('isRequired', False),
            'has_comment': self._has_comment_field(question_id, schema),
            'options': self.get_question_options(question_id)
        }
        
        # Add conditional logic information if present
        if 'visibleIf' in question_element:
            metadata['visible_if'] = question_element['visibleIf']
            metadata['visible_if_formatted'] = self._format_conditional_logic(question_element['visibleIf'])
        
        if 'enableIf' in question_element:
            metadata['enable_if'] = question_element['enableIf']
            metadata['enable_if_formatted'] = self._format_conditional_logic(question_element['enableIf'])

        metadata['dependencies'] = self.get_question_dependencies(question_id)
        
        return metadata
    
    def _format_conditional_logic(self, condition: str) -> str:
        """
        Format conditional logic for human-readable display.
        
        Args:
            condition: Raw conditional logic string
            
        Returns:
            Formatted conditional logic description
        """
        if not condition:
            return ""
        
        # Replace common operators with more readable versions
        formatted = condition
        
        # Replace field references with more readable names
        formatted = formatted.replace('{', '"').replace('}', '"')
        
        # Replace operators
        replacements = {
            ' = ': ' equals ',
            ' <> ': ' does not equal ',
            ' != ': ' does not equal ',
            ' > ': ' is greater than ',
            ' < ': ' is less than ',
            ' >= ': ' is greater than or equal to ',
            ' <= ': ' is less than or equal to ',
            ' anyof ': ' contains any of ',
            ' allof ': ' contains all of ',
            ' contains ': ' contains ',
            ' notcontains ': ' does not contain ',
            ' notempty': ' is not empty',
            ' empty': ' is empty',
            ' and ': ' AND ',
            ' or ': ' OR ',
            'true': 'Yes',
            'false': 'No'
        }
        
        for old, new in replacements.items():
            formatted = formatted.replace(old, new)
        
        # Clean up array notation
        formatted = formatted.replace("['", '"').replace("']", '"')
        formatted = formatted.replace("'", '"')
        
        return formatted
    
    def get_question_dependencies(self, question_id: str) -> List[str]:
        """
        Get list of question IDs that this question depends on.
        
        Args:
            question_id: ID of the question
            
        Returns:
            List of question IDs that this question depends on
        """
        schema = self._load_schema()
        question_element = self._find_question_element(question_id, schema)
        
        if not question_element:
            return []
        
        dependencies = []
        
        # Extract dependencies from visibleIf and enableIf conditions
        for condition_key in ['visibleIf', 'enableIf']:
            if condition_key in question_element:
                condition = question_element[condition_key]
                # Find all question references in the condition (format: {question-id})
                import re
                matches = re.findall(r'\{([^}]+)\}', condition)
                dependencies.extend(matches)
        
        # Remove duplicates and return
        return list(set(dependencies))
    
    def _load_schema(self) -> Dict[str, Any]:
        """Load and cache the survey schema."""
        if self._schema_cache is None:
            try:
                with open(self.schema_path, 'r', encoding='utf-8') as f:
                    self._schema_cache = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"Error loading schema from {self.schema_path}: {e}")
                self._schema_cache = {}
        
        return self._schema_cache
    
    def _load_custom_options(self) -> Dict[str, List[Any]]:
        """Load and cache custom options."""
        if self._custom_options_cache is None:
            try:
                with open(self.custom_options_path, 'r', encoding='utf-8') as f:
                    self._custom_options_cache = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"Error loading custom options from {self.custom_options_path}: {e}")
                self._custom_options_cache = {}
        
        return self._custom_options_cache
    
    def _find_question_element(self, question_id: str, schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find a question element in the schema by ID.
        
        Args:
            question_id: ID of the question to find
            schema: Survey schema dictionary
            
        Returns:
            Question element dictionary or None if not found
        """
        def search_elements(elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
            for element in elements:
                if element.get('name') == question_id:
                    return element
                
                # Search nested elements (e.g., in panels)
                if 'elements' in element:
                    result = search_elements(element['elements'])
                    if result:
                        return result
            
            return None
        
        # Search through all pages
        for page in schema.get('pages', []):
            if 'elements' in page:
                result = search_elements(page['elements'])
                if result:
                    return result
        
        return None
    
    def _has_comment_field(self, question_id: str, schema: Dict[str, Any]) -> bool:
        """
        Check if a question has an associated comment field.
        
        Args:
            question_id: ID of the question
            schema: Survey schema dictionary
            
        Returns:
            True if question has a comment field, False otherwise
        """
        # Look for a comment field with the pattern: question_id + "-Comment"
        comment_field_id = f"{question_id}-Comment"
        comment_element = self._find_question_element(comment_field_id, schema)
        return comment_element is not None