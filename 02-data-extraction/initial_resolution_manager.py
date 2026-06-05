"""
InitialResolutionManager class for managing initial conflict resolution data.

This module provides functionality to save and load initial resolution decisions
made by coders during the first stage of conflict resolution.
"""

import json
import re
from functools import lru_cache
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime, timezone
from response_manager import ResponseManager
from conflict_analyzer import ConflictAnalyzer


@lru_cache(maxsize=512)
def _load_json_cached(path_str: str, mtime_ns: int, size: int) -> Dict[str, Any]:
    with open(path_str, 'r', encoding='utf-8') as f:
        return json.load(f)


class InitialResolutionManager:
    """Manages reading and writing of initial resolution data."""
    
    def __init__(self, response_manager: ResponseManager, initial_resolutions_dir: str = "data/initial_resolutions", custom_options_path: str = 'data/custom-options.json'):
        """
        Initialize the InitialResolutionManager.
        
        Args:
            initial_resolutions_dir: Path to the directory containing initial resolution files
        """
        self.initial_resolutions_dir = Path(initial_resolutions_dir)
        self.initial_resolutions_dir.mkdir(parents=True, exist_ok=True)
        self.response_manager = response_manager
        self.conflict_analyzer = ConflictAnalyzer(custom_options_path)
    
    def _get_resolution_file_path(self, coder_name: str) -> Path:
        """Get the file path for a specific coder's resolutions."""
        return self.initial_resolutions_dir / f"resolved_{coder_name}.json"
    
    def _load_coder_resolutions(self, coder_name: str) -> Dict[str, Any]:
        """
        Load all resolutions for a specific coder.
        
        Args:
            coder_name: Name of the coder
            
        Returns:
            Dictionary mapping paper_id to resolution data
        """
        file_path = self._get_resolution_file_path(coder_name)
        
        try:
            stat = file_path.stat()
            return _load_json_cached(str(file_path), stat.st_mtime_ns, stat.st_size)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_coder_resolutions(self, coder_name: str, data: Dict[str, Any]) -> None:
        """
        Save all resolutions for a specific coder.
        
        Args:
            coder_name: Name of the coder
            data: Dictionary mapping paper_id to resolution data
        """
        file_path = self._get_resolution_file_path(coder_name)
        sorted_data = self._sort_dict(data)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(sorted_data, f, indent=2)
        _load_json_cached.cache_clear()
    
    def save_resolution(self, paper_id: str, coder_name: str, question_id: str, decision: str) -> bool:
        """
        Save a single resolution decision.
        
        Args:
            paper_id: ID of the paper
            coder_name: Name of the coder making the decision
            question_id: ID of the question
            decision: Decision made ('A', 'B', 'Union', or 'Discuss')
            
        Returns:
            True if save was successful, False otherwise
        """
        try:
            all_resolutions = self._load_coder_resolutions(coder_name)
            
            # Initialize paper entry if it doesn't exist
            if str(paper_id) not in all_resolutions:
                all_resolutions[str(paper_id)] = {
                    "resolver_name": coder_name,
                    "resolution_time": datetime.now(timezone.utc).isoformat(),
                    "resolutions": {}
                }
            
            # Update the specific question resolution
            all_resolutions[str(paper_id)]["resolutions"][question_id] = {
                "decision": decision,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Update overall resolution time
            all_resolutions[str(paper_id)]["resolution_time"] = datetime.now(timezone.utc).isoformat()
            
            # Save back to file
            self._save_coder_resolutions(coder_name, all_resolutions)
            return True
            
        except Exception as e:
            print(f"Error saving resolution: {e}")
            return False
    
    def get_resolutions(self, paper_id: str, coder_name: str) -> Dict[str, Any]:
        """
        Get all resolutions for a specific paper by a specific coder.
        
        Args:
            paper_id: ID of the paper
            coder_name: Name of the coder
            
        Returns:
            Dictionary containing resolution data for the paper
        """
        all_resolutions = self._load_coder_resolutions(coder_name)
        return all_resolutions.get(str(paper_id), {
            "resolver_name": coder_name,
            "resolution_time": None,
            "resolutions": {}
        })
    
    def get_all_resolutions(self, paper_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Get resolutions from all coders for a specific paper.
        
        Args:
            paper_id: ID of the paper
            
        Returns:
            Dictionary mapping coder names to their resolution data
        """
        result = {}
        
        # Find all resolution files
        for file_path in self.initial_resolutions_dir.glob("resolved_*.json"):
            coder_name = file_path.stem.replace("resolved_", "")
            resolutions = self.get_resolutions(paper_id, coder_name)
            
            if resolutions.get("resolutions"):  # Only include if they have resolutions
                result[coder_name] = resolutions
        
        return result
    
    def is_paper_ready_for_final(self, paper_id: str, required_coders: List[str]) -> Tuple[bool, List[str]]:
        """
        Check if a paper is ready for final resolution.
        
        A paper is ready when all required coders have completed their initial resolutions.
        
        Args:
            paper_id: ID of the paper
            required_coders: List of coder names that must complete initial resolution
            
        Returns:
            Tuple of (is_ready, list_of_coders_who_completed)
        """
        all_resolutions = self.get_all_resolutions(paper_id)
        completed_coders = []
        
        for coder_name in required_coders:
            if coder_name in all_resolutions:
                resolutions = all_resolutions[coder_name].get("resolutions", {})
                if resolutions:  # Has at least one resolution
                    completed_coders.append(coder_name)
        
        is_ready = len(completed_coders) >= 2  # At least 2 coders completed
        return is_ready, completed_coders
    
    def get_papers_ready_for_final(self, all_paper_ids: List[str], required_coders: List[str]) -> List[str]:
        """
        Get list of papers that are ready for final resolution.
        
        Args:
            all_paper_ids: List of all paper IDs to check
            required_coders: List of coder names that must complete initial resolution
            
        Returns:
            List of paper IDs ready for final resolution
        """
        ready_papers = []
        
        for paper_id in all_paper_ids:
            is_ready, _ = self.is_paper_ready_for_final(paper_id, required_coders)
            if is_ready:
                ready_papers.append(paper_id)
        
        return ready_papers
    
    def get_resolution_status(self, paper_id: str) -> Dict[str, Any]:
        """
        Get the resolution status for a paper.
        
        Args:
            paper_id: ID of the paper
            
        Returns:
            Dictionary with status information
        """
        all_resolutions = self.get_all_resolutions(paper_id)
        conflicts = self.conflict_analyzer.find_conflicts(self.response_manager.load_paper_responses(paper_id))
        
        status = {
            "paper_id": paper_id,
            "coders": {},
            "total_coders": len(all_resolutions),
            "is_complete": len(all_resolutions) >= 2
        }
        
        for coder_name, data in all_resolutions.items():
            resolutions = data.get("resolutions", {})
            status["coders"][coder_name] = {
                "completed": len(resolutions) == len(conflicts),
                "resolution_count": len(resolutions),
                "resolution_time": data.get("resolution_time")
            }
        
        return status
    
    def _sort_dict(self, d: Any) -> Any:
        """
        Sort dictionary with numeric prefix keys first.
        
        This maintains compatibility with the existing sort_dict utility.
        """
        def numeric_prefix_key(k):
            match = re.match(r'^(\d+)', str(k))
            is_comment = str(k).endswith('-Comment')
            if match:
                return (0, int(match.group(1)), 1 if is_comment else 0, str(k))
            else:
                return (1, 0, 1 if is_comment else 0, str(k))

        if isinstance(d, dict):
            sorted_items = sorted(d.items(), key=lambda item: numeric_prefix_key(item[0]))
            return {k: self._sort_dict(v) for k, v in sorted_items}
        elif isinstance(d, list):
            return [self._sort_dict(item) for item in d]
        else:
            return d
