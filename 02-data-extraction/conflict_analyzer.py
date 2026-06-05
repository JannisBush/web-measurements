"""
ConflictAnalyzer class for identifying conflicts between coder responses.

This module provides functionality to analyze responses from multiple coders
and identify questions where disagreements exist.
"""

import json
from functools import lru_cache
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path


@lru_cache(maxsize=512)
def _load_json_cached(path_str: str, mtime_ns: int, size: int) -> Dict[str, Any]:
    with open(path_str, 'r', encoding='utf-8') as f:
        return json.load(f)


class ConflictAnalyzer:
    """Analyzes responses to identify conflicts between coders."""
    
    def __init__(self, custom_options_path: str = "data/custom-options.json"):
        """
        Initialize the ConflictAnalyzer.
        
        Args:
            custom_options_path: Path to the custom options JSON file
        """
        self.custom_options_path = Path(custom_options_path)
    
    def find_conflicts(self, paper_responses: List[Dict[str, Any]]) -> List[str]:
        """
        Find conflicts between coder responses for a paper.
        
        Args:
            paper_responses: List of response entries for a paper, each containing
                           extractor_name, submission_time, and data fields
        
        Returns:
            List of question IDs where coders provided different answers
        """
        # Get valid coder responses (first two)
        valid_coder_responses = self._get_valid_coder_responses(paper_responses)
        
        if len(valid_coder_responses) < 2:
            return []
        
        conflicts = []
        
        # Get all question IDs from the selected responses
        all_questions = set()
        for response in valid_coder_responses:
            all_questions.update([q for q in response['data'].keys()])
        
        # Filter out questions that should not be considered conflicts
        excluded_from_conflicts = {
            '1-q-p0-name',  # Coder name field - should be auto-populated
            '2-q-p0-papertype',  # Paper type field - always use first coder's value
            'pageNo'  # Page number - not a real question
        }

        # Excluded paper, not an active measurement -> no conflicts
        if '11-q-p1-major-4-noactiveconffinal' in all_questions:
            if valid_coder_responses[0]["data"].get('11-q-p1-major-4-noactiveconffinal', True) == valid_coder_responses[1]["data"].get('11-q-p1-major-4-noactiveconffinal', True):
                return []
        
        # Check each question for conflicts
        for question_id in all_questions:
            # Skip excluded questions and meta fields and comments
            if (question_id in excluded_from_conflicts or 
                question_id.endswith('-added') or
                question_id.endswith('-Comment')):
                continue
                
            if self._has_conflict(question_id, valid_coder_responses):
                conflicts.append(question_id)
        
        return sorted(conflicts)
    
    def find_comment_conflicts(self, paper_responses: List[Dict[str, Any]]) -> List[str]:
        """
        Find conflicts in comment fields only.
        
        Args:
            paper_responses: List of response entries for a paper
            
        Returns:
            List of comment field IDs where coders provided different comments
        """
        # Get valid coder responses (first two)
        valid_coder_responses = self._get_valid_coder_responses(paper_responses)
        
        if len(valid_coder_responses) < 2:
            return []
        
        comment_conflicts = []
        
        # Get all comment fields from the selected responses
        all_comment_fields = set()
        for response in valid_coder_responses:
            for field_id in response['data'].keys():
                if field_id.endswith('-Comment'):
                    all_comment_fields.add(field_id)
        
        # Check each comment field for conflicts
        for comment_field_id in all_comment_fields:
            if self._has_conflict(comment_field_id, valid_coder_responses):
                comment_conflicts.append(comment_field_id)
        
        return sorted(comment_conflicts)
    
    def get_question_with_comments(self, question_id: str, paper_responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get question data including associated comment fields.
        
        Args:
            question_id: ID of the main question
            paper_responses: List of response entries for a paper
            
        Returns:
            Dictionary containing main response and comment data
        """
        valid_coder_responses = self._get_valid_coder_responses(paper_responses)
        comment_field_id = f"{question_id}-Comment"
        
        result = {
            'question_id': question_id,
            'comment_field_id': comment_field_id,
            'has_main_conflict': self._has_conflict(question_id, valid_coder_responses),
            'has_comment_conflict': self._has_conflict(comment_field_id, valid_coder_responses),
            'coder_data': {}
        }
        
        # Get data for each coder
        for response in valid_coder_responses:
            coder_name = response['extractor_name'][0]
            result['coder_data'][coder_name] = {
                'main_response': response['data'].get(question_id),
                'comment': response['data'].get(comment_field_id, '')
            }
        
        return result
    
    def get_coder_responses(self, paper_responses: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Get structured coder response data for valid coders only.
        
        Args:
            paper_responses: List of response entries for a paper
            
        Returns:
            Dictionary with coder names as keys and their response data as values
        """
        coder_data = {}
        valid_coder_responses = self._get_valid_coder_responses(paper_responses)
        
        for response in valid_coder_responses:
            extractor_name = response['extractor_name'][0]
            
            # Filter out meta fields and pageNo from responses
            filtered_responses = {k: v for k, v in response['data'].items() 
                                if not k.endswith('-added') and k != 'pageNo'}
            
            coder_data[extractor_name] = {
                'name': extractor_name,
                'responses': filtered_responses,
                'submission_time': response.get('submission_time', '')
            }
        
        return coder_data
    
    def _has_conflict(self, question_id: str, coder_responses: List[Dict[str, Any]]) -> bool:
        """
        Check if a specific question has conflicts between coders.
        
        Args:
            question_id: ID of the question to check
            coder_responses: List of coder response entries
            
        Returns:
            True if there's a conflict, False otherwise
        """
        values = []
        
        for response in coder_responses:
            data = response['data']
            if question_id in data:
                # Normalize the value for comparison
                values.append(self._normalize_value(data[question_id]))
            else:
                # Treat missing values as empty/None for comparison
                values.append(None)
        
        return values[0] != values[1]
            
    def _normalize_value(self, value: Any) -> Any:
        """
        Normalize a value for comparison.
        
        Args:
            value: The value to normalize
            
        Returns:
            Normalized value
        """
        if value is None:
            return None
        elif isinstance(value, list):
            # Sort lists for consistent comparison
            return sorted([str(item) for item in value])
        elif isinstance(value, dict):
            # For dict values, convert to sorted tuple of items
            return tuple(sorted(value.items()))
        else:
            return str(value).strip()  # Strip whitespace for string comparison
    
    def get_available_coders(self, paper_responses: List[Dict[str, Any]]) -> List[str]:
        """
        Get list of available valid coders for a paper.
        
        Args:
            paper_responses: List of response entries for a paper
            
        Returns:
            List of valid coder names
        """
        valid_coders = self._get_valid_coders()
        available_coders = []
        
        for response in paper_responses:
            coder_name = response['extractor_name'][0]
            if coder_name in valid_coders:
                available_coders.append(coder_name)
            else:
                print(f"Warning: Coder '{coder_name}' is not in the list of valid coders.")
        
        return available_coders
    
    def _get_valid_coder_responses(self, paper_responses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Get responses from the first two valid coders.
        
        Args:
            paper_responses: List of response entries for a paper
            
        Returns:
            List of the first two valid coder responses
        """
        valid_coders = self._get_valid_coders()
        valid_responses = []
        
        for response in paper_responses:
            coder_name = response['extractor_name'][0]
            
            # Skip if not a valid coder
            if coder_name not in valid_coders:
                continue
            
            valid_responses.append(response)
        
        # Always take first two valid responses
        if len(valid_responses) > 2:
            return Exception("More than two valid coders found. This should not happen.")
        
        return valid_responses
    
    def _get_valid_coders(self) -> List[str]:
        """
        Get list of valid coder names from custom-options.json.
        
        Returns:
            List of valid coder names
        """
        try:
            stat = self.custom_options_path.stat()
            custom_options = _load_json_cached(str(self.custom_options_path), stat.st_mtime_ns, stat.st_size)
            
            # Get coder names from the "1-q-p0-name" field
            name_options = custom_options.get("1-q-p0-name", [])
            return [option['value'] for option in name_options]
                    
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading valid coders from {self.custom_options_path}: {e}")
            return []