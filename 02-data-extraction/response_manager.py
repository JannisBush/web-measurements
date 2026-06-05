"""
ResponseManager class for managing response data operations.

This module provides functionality to load, save, and manipulate response data
while maintaining data integrity and structure.
"""

import json
import re
from functools import lru_cache
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime, timezone


@lru_cache(maxsize=512)
def _load_json_cached(path_str: str, mtime_ns: int, size: int) -> Dict[str, Any]:
    with open(path_str, 'r', encoding='utf-8') as f:
        return json.load(f)


@lru_cache(maxsize=512)
def _load_merged_responses_cached(signature: tuple[tuple[str, int, int], ...]) -> Dict[str, List[Dict[str, Any]]]:
    merged_responses: Dict[str, List[Dict[str, Any]]] = {}

    for path_str, _, _ in signature:
        try:
            with open(path_str, 'r', encoding='utf-8') as f:
                coder_responses = json.load(f)

            for paper_id, response_list in coder_responses.items():
                if paper_id not in merged_responses:
                    merged_responses[paper_id] = []
                merged_responses[paper_id].extend(response_list)

        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading responses from {path_str}: {e}")
            continue

    return merged_responses

def find_object_by_name(data, target_name):
    if isinstance(data, list):
        for item in data:
            result = find_object_by_name(item, target_name)
            if result is not None:
                return result

    elif isinstance(data, dict):
        if data.get("name") == target_name:
            return data

        for value in data.values():
            result = find_object_by_name(value, target_name)
            if result is not None:
                return result

    return None


class ResponseManager:
    """Manages reading and writing of response data."""
    
    def __init__(self, responses_dir: str = "data/responses", 
                 final_responses_path: str = "data/final_responses.json",
                 schema_path: str = "data/surveyjson.json"):
        """
        Initialize the ResponseManager.
        
        Args:
            responses_dir: Path to the directory containing coder-specific response files
            final_responses_path: Path to the final responses JSON file
        """
        self.responses_dir = Path(responses_dir)
        self.final_responses_path = Path(final_responses_path)
        self.schema_path = schema_path
    
    def _get_all_responses_paths(self):
        """Get all coder-specific response file paths."""
        if not self.responses_dir.exists():
            return []
        return list(self.responses_dir.glob("responses_*.json"))

    def _get_all_responses_signature(self):
        """Get a cache key that changes whenever any response file changes."""
        signature = []
        for responses_path in sorted(self._get_all_responses_paths()):
            stat = responses_path.stat()
            signature.append((str(responses_path), stat.st_mtime_ns, stat.st_size))
        return tuple(signature)
    
    def load_paper_responses(self, paper_id: str) -> List[Dict[str, Any]]:
        """
        Load all responses for a specific paper.
        
        Args:
            paper_id: ID of the paper
            
        Returns:
            List of response entries for the paper
        """
        all_responses = self._load_all_responses()
        return all_responses.get(str(paper_id), [])
    
    def delete_final_response(self, paper_id: str, question_id: str) -> bool:
        """
        Delete a final response for a specific question.
        
        Args:
            paper_id: ID of the paper
            question_id: ID of the question
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            final_responses = self._load_final_responses()
            
            if str(paper_id) not in final_responses:
                # No final response exists, nothing to delete
                return True
            
            # Remove the specific question from final data
            if "data" in final_responses[str(paper_id)] and question_id in final_responses[str(paper_id)]["data"]:
                del final_responses[str(paper_id)]["data"][question_id]
                
                # If no questions left, remove the paper entry entirely
                if not final_responses[str(paper_id)]["data"]:
                    del final_responses[str(paper_id)]
            
            # Save updated final responses
            self._save_final_responses(final_responses)
            return True
            
        except Exception as e:
            print(f"Error deleting final response: {e}")
            return False

    def _create_final_response_entry(self, paper_id: str) -> Dict[str, Any]:
        """
        Create a new final response entry with metadata.
        
        Args:
            paper_id: ID of the paper
            
        Returns:
            New final response entry with extractor_name, submission_time, and empty data
        """
        # Get coder names for metadata
        paper_responses = self.load_paper_responses(paper_id)
        coder_names = list({response['extractor_name'][0] for response in paper_responses})
        
        extractor_name = "+".join(coder_names[:2]) + "+final" if len(coder_names) >= 2 else "final"
        
        return {
            "extractor_name": [extractor_name],
            "submission_time": datetime.now(timezone.utc).isoformat(),
            "data": {}
        }
    
    def save_final_response(self, paper_id: str, question_id: str, value: Any) -> bool:
        """
        Update final response for a specific question.
        
        Args:
            paper_id: ID of the paper
            question_id: ID of the question
            value: New value for the final response
            
        Returns:
            True if save was successful, False otherwise
        """
        try:
            final_responses = self._load_final_responses()
            
            # Update the specific question
            final_responses[str(paper_id)]["data"][question_id] = value
            # Update timestamp
            final_responses[str(paper_id)]["submission_time"] = datetime.now(timezone.utc).isoformat()
            
            # Save updated final responses
            self._save_final_responses(final_responses)
            return True
            
        except Exception as e:
            print(f"Error saving final response: {e}")
            return False
    
    def auto_populate_final_responses(self, paper_id: str) -> bool:
        """
        Auto-populate final responses with non-conflicted data.
        
        This method:
        1. Fills non-conflicted questions with the first coder's responses
        2. Auto-fills comment fields where only one coder provided a comment
        
        Args:
            paper_id: ID of the paper
            
        Returns:
            True if population was successful, False otherwise
        """
        try:
            from conflict_analyzer import ConflictAnalyzer
            
            paper_responses = self.load_paper_responses(paper_id)
            if len(paper_responses) < 2:
                return False
            
            # Find conflicts using first two valid coders
            analyzer = ConflictAnalyzer()
            conflicts = analyzer.find_conflicts(paper_responses)
            comment_conflicts = analyzer.find_comment_conflicts(paper_responses)
            
            # Get valid coder responses
            coder_data = analyzer.get_coder_responses(paper_responses)
            
            if len(coder_data) < 2:
                return False
            
            # Get all questions from first valid coder
            coder_names = list(coder_data.keys())
            first_coder = coder_names[0]
            second_coder = coder_names[1]
            coder1_data = coder_data[first_coder]['responses']
            coder2_data = coder_data[second_coder]['responses']
            
            # Combine all conflicts (main + comment conflicts)
            all_conflicts = set(conflicts + comment_conflicts)
            
            # Load existing final responses
            final_responses = self._load_final_responses()
            if str(paper_id) not in final_responses:
                final_responses[str(paper_id)] = self._create_final_response_entry(paper_id)
            
            # Populate non-conflicted questions with coder 1 values
            for question_id, value in coder1_data.items():
                # Skip if already has a final value
                if question_id in final_responses[str(paper_id)]["data"]:
                    continue
                if question_id not in all_conflicts:
                    final_responses[str(paper_id)]["data"][question_id] = value
            
            # Set the final name field to the combined coder names
            final_responses[str(paper_id)]["data"]['1-q-p0-name'] = final_responses[str(paper_id)]["extractor_name"]
            
            # Set the papertype field to the first coder's value (always use first coder's papertype)
            if '2-q-p0-papertype' in coder1_data:
                final_responses[str(paper_id)]["data"]['2-q-p0-papertype'] = coder1_data['2-q-p0-papertype']
            
            # Auto-fill comment fields
            all_comment_fields = set()
            # Collect all comment fields from both coders
            for question_id in coder1_data.keys():
                if question_id.endswith('-Comment'):
                    all_comment_fields.add(question_id)
            for question_id in coder2_data.keys():
                if question_id.endswith('-Comment'):
                    all_comment_fields.add(question_id)
            
            # Check each comment field for auto-fill potential
            for question_id in all_comment_fields:
                # Skip if already has a final value
                if question_id in final_responses[str(paper_id)]["data"]:
                    continue
                
                coder1_value = coder1_data.get(question_id, '')
                coder2_value = coder2_data.get(question_id, '')
                
                # Auto-fill if exactly one coder has a comment
                coder1_has_comment = coder1_value and str(coder1_value).strip() != ''
                coder2_has_comment = coder2_value and str(coder2_value).strip() != ''

                final_comment = ''    
                if (coder1_has_comment):
                    # Prefix with coder name
                    final_comment += f"({first_coder}:) {coder1_value};"
                if (coder2_has_comment):
                    # Prefix with coder name
                     final_comment += f"({second_coder}:) {coder2_value};"
                if len(final_comment):
                    final_responses[str(paper_id)]["data"][question_id] = final_comment

            # Save updated final responses
            self._save_final_responses(final_responses)
            return True
            
        except Exception as e:
            print(f"Error populating default final responses: {e}")
            return False
    
    def auto_populate_from_initial_resolutions(self, paper_id: str, initial_resolutions_dir: str = "data/initial_resolutions") -> bool:
        """
        Auto-populate final responses based on initial resolution agreements.
        
        Rules:
        - Both said "A": Use Coder A's response
        - Both said "B": Use Coder B's response
        - Both said "Union":
          - Multi-select: Union of both responses
          - Free-text: "(Coder A): resp1; (Coder B): resp2"
        - Any "Discuss" or disagreement: Leave empty for manual resolution
        
        Args:
            paper_id: ID of the paper
            initial_resolutions_dir: Path to initial resolutions directory
            
        Returns:
            True if population was successful, False otherwise
        """
        try:
            from conflict_analyzer import ConflictAnalyzer
            from initial_resolution_manager import InitialResolutionManager
            from pathlib import Path
            
            paper_responses = self.load_paper_responses(paper_id)
            if len(paper_responses) < 2:
                return False
            
            # Get coder data and conflicts
            analyzer = ConflictAnalyzer()
            conflicts = analyzer.find_conflicts(paper_responses)
            coder_data = analyzer.get_coder_responses(paper_responses)
            
            if len(coder_data) < 2:
                return False
            
            coder_names = list(coder_data.keys())
            first_coder = coder_names[0]
            second_coder = coder_names[1]
            coder1_data = coder_data[first_coder]['responses']
            coder2_data = coder_data[second_coder]['responses']
            
            # Load initial resolutions
            initial_manager = InitialResolutionManager(Path(initial_resolutions_dir))
            all_initial_resolutions = initial_manager.get_all_resolutions(paper_id)
            
            if len(all_initial_resolutions) < 2:
                # Fall back to old auto-populate if initial resolutions not available
                return self.auto_populate_final_responses(paper_id)
            
            # Get resolutions from both coders
            coder1_resolutions = all_initial_resolutions.get(first_coder, {}).get("resolutions", {})
            coder2_resolutions = all_initial_resolutions.get(second_coder, {}).get("resolutions", {})

            with open(self.schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            
            # Load or create final responses entry
            final_responses = self._load_final_responses()
            if str(paper_id) not in final_responses:
                final_responses[str(paper_id)] = self._create_final_response_entry(paper_id)
            
            # Auto-fill non-conflicted questions first (same as before)
            for question_id, value in coder1_data.items():
                if question_id in final_responses[str(paper_id)]["data"]:
                    continue
                if question_id not in conflicts and not question_id.endswith('-Comment'):
                    final_responses[str(paper_id)]["data"][question_id] = value
            
            # Set metadata fields
            final_responses[str(paper_id)]["data"]['1-q-p0-name'] = final_responses[str(paper_id)]["extractor_name"]
            if '2-q-p0-papertype' in coder1_data:
                final_responses[str(paper_id)]["data"]['2-q-p0-papertype'] = coder1_data['2-q-p0-papertype']


            
            # Process conflicts based on initial resolutions
            for question_id in conflicts:
                # Skip if already has a final value
                if question_id in final_responses[str(paper_id)]["data"]:
                    continue
                
                decision1 = coder1_resolutions.get(question_id, {}).get('decision', '')
                decision2 = coder2_resolutions.get(question_id, {}).get('decision', '')
                q_meta = find_object_by_name(schema, question_id)
                
                if decision1 == decision2 and decision1:
                    # Both coders agreed on the decision
                    if decision1 == first_coder:
                        # Both chose first coder's response
                        value = coder1_data.get(question_id)
                        if q_meta["type"] in ["text", "comment"] and q_meta.get("inputType", None) != "number":
                            value = f"({first_coder}): {value}"
                        final_responses[str(paper_id)]["data"][question_id] = value
                    elif decision1 == second_coder:
                        # Both chose second coder's response
                        value = coder1_data.get(question_id)
                        if q_meta["type"] in ["text", "comment"] and q_meta.get("inputType", None) != "number":
                            value = f"({second_coder}): {value}"
                        final_responses[str(paper_id)]["data"][question_id] = coder2_data.get(question_id)
                    elif decision1 == 'Union':
                        # Create union based on question type
                        value1 = coder1_data.get(question_id)
                        value2 = coder2_data.get(question_id)
                        
                        # Check if it's a multi-select (array) or free-text
                        
                        if q_meta["type"] == "checkbox":
                            # Multi-select: union of both
                            set1 = set(value1 if isinstance(value1, list) else [value1] if value1 else [])
                            set2 = set(value2 if isinstance(value2, list) else [value2] if value2 else [])
                            union = list(set1 | set2)
                            final_responses[str(paper_id)]["data"][question_id] = union
                        elif q_meta["type"] in ["text", "comment"] and q_meta.get("inputType", None) != "number":
                            # Free-text: combine with coder names
                            parts = []
                            if value1 and str(value1).strip():
                                parts.append(f"({first_coder}): {value1}")
                            if value2 and str(value2).strip():
                                parts.append(f"({second_coder}): {value2}")
                            if parts:
                                final_responses[str(paper_id)]["data"][question_id] = "; ".join(parts)
                        else:
                            print(f"Invalid question chosen with union!: {q_meta}")
                    # If decision is 'Discuss', leave empty for manual resolution
                # If disagreement, leave empty for manual resolution
            
            # Handle comment fields (always combine if present)
            all_comment_fields = set()
            for question_id in list(coder1_data.keys()) + list(coder2_data.keys()):
                if question_id.endswith('-Comment'):
                    all_comment_fields.add(question_id)
            
            for question_id in all_comment_fields:
                if question_id in final_responses[str(paper_id)]["data"]:
                    continue
                
                coder1_value = coder1_data.get(question_id, '')
                coder2_value = coder2_data.get(question_id, '')
                
                coder1_has_comment = coder1_value and str(coder1_value).strip() != ''
                coder2_has_comment = coder2_value and str(coder2_value).strip() != ''
                
                parts = []
                if coder1_has_comment:
                    parts.append(f"({first_coder}:) {coder1_value}")
                if coder2_has_comment:
                    parts.append(f"({second_coder}:) {coder2_value}")
                
                if parts:
                    final_responses[str(paper_id)]["data"][question_id] = "; ".join(parts)
            
            # Save updated final responses
            self._save_final_responses(final_responses)
            return True
            
        except Exception as e:
            print(f"Error populating from initial resolutions: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_all_papers_with_multiple_responses(self) -> Dict[str, List[str]]:
        """
        Get dictionary of paper IDs that have multiple valid coder responses with their coders.
        
        Returns:
            Dictionary mapping paper IDs to lists of coder names
        """
        from conflict_analyzer import ConflictAnalyzer
        
        all_responses = self._load_all_responses()
        papers_with_multiple = {}
        analyzer = ConflictAnalyzer()
        
        for paper_id, responses in all_responses.items():
            # Get available valid coders
            available_coders = analyzer.get_available_coders(responses)
            
            if len(available_coders) >= 2:
                papers_with_multiple[paper_id] = available_coders
        
        return papers_with_multiple
    
    def _load_all_responses(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load all responses from all coder-specific files and merge them.
        
        Returns:
            Dictionary mapping paper_id to list of all responses from all coders
        """
        return _load_merged_responses_cached(self._get_all_responses_signature())
    
    def _load_final_responses(self) -> Dict[str, Dict[str, Any]]:
        """Load all final responses from the final responses JSON file."""
        try:
            stat = self.final_responses_path.stat()
            return _load_json_cached(str(self.final_responses_path), stat.st_mtime_ns, stat.st_size)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            # File doesn't exist yet, return empty dict
            return {}
    
    def _save_final_responses(self, data: Dict[str, Dict[str, Any]]) -> None:
        """Save all final responses to the final responses JSON file."""
        sorted_data = self._sort_dict(data)
        with open(self.final_responses_path, "w", encoding='utf-8') as f:
            json.dump(sorted_data, f, indent=2)
        _load_json_cached.cache_clear()
    
    def _sort_dict(self, d: Any) -> Any:
        """
        Sort dictionary with numeric prefix keys first.
        
        This maintains compatibility with the existing sort_dict utility in app.py.
        """
        def numeric_prefix_key(k):
            match = re.match(r'^(\d+)', str(k))
            is_comment = str(k).endswith('-Comment')
            if match:
                # Return (priority, numeric_prefix, is_comment, full_key)
                # is_comment=True (1) sorts after is_comment=False (0)
                return (0, int(match.group(1)), 1 if is_comment else 0, str(k))
            else:
                return (1, 0, 1 if is_comment else 0, str(k))

        if isinstance(d, dict):
            # Sort this level
            sorted_items = sorted(d.items(), key=lambda item: numeric_prefix_key(item[0]))
            # Recurse into values
            return {k: self._sort_dict(v) for k, v in sorted_items}
        elif isinstance(d, list):
            # For lists, recurse into elements
            return [self._sort_dict(item) for item in d]
        else:
            # Return primitive as is
            return d
        
    def is_question_removed_by_dependency(self, question_id, paper_id):
        """
        Check if a question was removed due to dependency rules.
        :param question_id: str, ID of the question
        :param paper_id: str, ID of the paper
        :return: bool
        """
        dependency_rules = {
            '31-q-p2-setup-implementation-2-browserbased': {
                'condition': lambda value: value in [False, 'false', 'No'],
                'dependentQuestions': [
                    '32-q-p2-setup-implementation-3-automation',
                    '34-q-p2-setup-implementation-5-browserused',
                    '35-q-p2-setup-implementation-6-browserversion',
                    '36-q-p2-setup-implementation-6-browserinstrumentation',
                    '37-q-p2-setup-implementation-7-browserext',
                    '38-q-p2-setup-implementation-8-headless',
                    '39-q-p2-setup-implementation-9-dimensions',
                    '40-q-p2-setup-implementation-10-incognito',
                    '62-q-p2-process-5-pageinteraction'
                ]
            },
            '24-q-p2-dataset-webpage-2-internal': {
                'condition': lambda value: value in [False, 'false', 'No'],
                'dependentQuestions': [
                    '25-q-p2-dataset-webpage-3-internalselection',
                    '26-q-p2-dataset-webpage-4-internalsize',
                    '26-27-q-p2-dataset-webpage-4-internalsize-details',
                    '28-q-p2-dataset-webpage-5-internallock',
                    '29-q-p2-dataset-webpage-6-robots'
                ]
            },
            '76-q-p3-factors-1-factors': {
                'condition': lambda value: value in [False, 'false', 'No'],
                'dependentQuestions': [
                    '77-q-p3-factors-2-factorsloc',
                    '78-q-p3-factors-3-factorscat',
                    '79-q-p3-factors-4-dataset',
                    '80-q-p3-factors-5-implementation',
                    '81-q-p3-factors-6-env',
                    '82-q-p3-factors-7-process',
                    '83-q-p3-factors-8-reporting',
                    '84-q-p3-factors-9-other'
                ]
            },
            '85-q-p3-factortesting-1-testing': {
                'condition': lambda value: value in [False, 'false', 'No'],
                'dependentQuestions': [
                    '86-q-p3-factortesting-2-which',
                    '87-q-p3-factortesting-3-core'
                ]
            },
            # Question 69 controls question 70
            '69-q-p2-crawlmultiple-1-multiple': {
                'condition': lambda value: self._parse_int(value) <= 1,
                'dependentQuestions': [
                    '70-q-p2-crawlmultiple-2-multipledetails'
                ]
            },
            # Question 78 controls questions 79-84 (multi-select)
            '78-q-p3-factors-3-factorscat': {
                'type': 'multiselect',
                'dependentQuestions': {
                    '79-q-p3-factors-4-dataset': 'Dataset',
                    '80-q-p3-factors-5-implementation': 'Crawler Implementation',
                    '81-q-p3-factors-6-env': 'Crawling Environment',
                    '82-q-p3-factors-7-process': 'Crawling Setup',
                    '83-q-p3-factors-8-reporting': 'Analysis & Reporting',
                    '84-q-p3-factors-9-other': 'Other/Ungrouped'
                }
            },
            '95-q-p4-practices-7-code': {
                'condition': lambda value: value not in ['Yes', 'Partially', 'Dead link', 'Empty repo'],
                'dependentQuestions': [
                    '97-q-p4-practices-9-codewhere'
                ]
            },
            '96-q-p4-practices-8-data': {
                'condition': lambda value: value not in ['Yes', 'Partially', 'Dead link', 'Empty repo'],
                'dependentQuestions': [
                    '98-q-p4-practices-10-datawhere'
                ]
            },
             '12-q-p1-major-5-datasetsource': {
                'condition': lambda value: value not in ['DB/Archive'],
                'dependentQuestions': [
                    '13-q-p1-major-6-datasetused'
                ]
            },
            '60-q-p2-process-4-pagestay': {
                'condition': lambda value: value not in ['specified'],
                'dependentQuestions': [ 
                    '60-61-q-p2-process-4-pagestay-seconds'
                ]
            },
            '62-q-p2-process-5-pageinteraction': {
                'condition': lambda value: value not in [True, 'true'],
                'dependentQuestions': [ 
                    '63-q-p2-process-6-pageinteractiondetails'
                ]
            }
        }

        # Load existing final responses
        final_responses = self._load_final_responses().get(paper_id)
        if not final_responses:
            return False
        
        final_data = final_responses.get("data", {})
        
        # Check standard dependency rules
        for parent_id, rule in dependency_rules.items():
            if rule.get('type') == 'multiselect':
                # Handle multi-select dependencies (question 78)
                if question_id in rule['dependentQuestions']:
                    parent_value = final_data.get(parent_id)
                    required_value = rule['dependentQuestions'][question_id]
                    
                    # Convert parent_value to list if needed
                    parent_list = parent_value if isinstance(parent_value, list) else (
                        [parent_value] if parent_value else []
                    )

                    if len(parent_list) == 0:
                        return False
                    
                    # If required value is NOT in parent list, question should be removed
                    if required_value not in parent_list:
                        return True
            else:
                # Handle standard binary dependencies
                if question_id in rule['dependentQuestions']:
                    parent_value = final_data.get(parent_id)
                    if parent_value is not None and rule['condition'](parent_value):
                        return True

        return False
    
    def _parse_int(self, value):
        """Helper to safely parse integer values."""
        try:
            if isinstance(value, int):
                return value
            if isinstance(value, str):
                return int(value)
            return 0
        except (ValueError, TypeError):
            return 0