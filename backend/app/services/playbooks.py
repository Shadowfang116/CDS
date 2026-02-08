"""Playbooks service for loading and managing authority playbooks."""
import os
import logging
from typing import List, Dict, Any, Optional
import yaml

logger = logging.getLogger(__name__)

# Path to playbooks YAML
PLAYBOOKS_PATH = os.environ.get("PLAYBOOKS_PATH", "/app/docs/10_playbooks_v1.yaml")

# Cache for playbooks
_playbooks_cache: Optional[Dict[str, Any]] = None


def load_playbooks() -> Dict[str, Any]:
    """Load playbooks YAML. Cached in memory."""
    global _playbooks_cache
    
    if _playbooks_cache is not None:
        return _playbooks_cache
    
    try:
        with open(PLAYBOOKS_PATH, "r", encoding="utf-8") as f:
            _playbooks_cache = yaml.safe_load(f)
            return _playbooks_cache
    except FileNotFoundError:
        logger.warning(f"Playbooks not found at {PLAYBOOKS_PATH}, returning empty")
        return {"playbooks": []}
    except Exception as e:
        logger.error(f"Failed to load playbooks: {e}")
        return {"playbooks": []}


def get_active_playbooks(regime: Optional[str]) -> List[Dict[str, Any]]:
    """
    Get active playbooks for a regime.
    
    Args:
        regime: Regime enum value (e.g., "LDA", "DHA")
    
    Returns:
        List of playbook dicts matching the regime
    """
    playbooks_data = load_playbooks()
    playbooks = playbooks_data.get("playbooks", [])
    
    if not regime:
        return []
    
    regime_upper = regime.upper()
    matching = []
    
    for pb in playbooks:
        pb_regimes = [r.upper() for r in pb.get("regimes", [])]
        if regime_upper in pb_regimes:
            matching.append(pb)
    
    return matching


def get_required_evidence(playbooks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Get flattened list of required evidence from playbooks with deduplication.
    
    Args:
        playbooks: List of playbook dicts
    
    Returns:
        List of evidence items (deduplicated by code)
    """
    evidence_map: Dict[str, Dict[str, Any]] = {}
    
    for pb in playbooks:
        evidence_list = pb.get("required_evidence", [])
        for ev in evidence_list:
            code = ev.get("code")
            if code and code not in evidence_map:
                evidence_map[code] = ev
    
    return list(evidence_map.values())


def get_playbook_by_id(playbook_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific playbook by ID."""
    playbooks_data = load_playbooks()
    playbooks = playbooks_data.get("playbooks", [])
    
    for pb in playbooks:
        if pb.get("id") == playbook_id:
            return pb
    
    return None

