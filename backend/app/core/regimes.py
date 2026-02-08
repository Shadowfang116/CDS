"""Regime classification for property jurisdiction."""
from enum import Enum
from typing import Optional, Tuple, List


class Regime(str, Enum):
    """Canonical property regimes."""
    REVENUE = "REVENUE"
    SOCIETY = "SOCIETY"
    LDA = "LDA"
    RUDA = "RUDA"
    DHA = "DHA"
    CANTONMENT = "CANTONMENT"
    MUNICIPAL = "MUNICIPAL"
    UNKNOWN = "UNKNOWN"


def normalize_regime(input_str: Optional[str]) -> Optional[Regime]:
    """
    Normalize regime string to canonical enum.
    
    Examples:
        "LDA" -> Regime.LDA
        "DHA Phase" -> Regime.DHA
        "Cantonment Board" -> Regime.CANTONMENT
    """
    if not input_str:
        return None
    
    normalized = input_str.upper().strip()
    
    # Direct matches
    for regime in Regime:
        if normalized == regime.value:
            return regime
    
    # Aliases
    aliases = {
        "LDA": Regime.LDA,
        "LAHORE DEVELOPMENT AUTHORITY": Regime.LDA,
        "DHA": Regime.DHA,
        "DEFENCE HOUSING AUTHORITY": Regime.DHA,
        "DHA PHASE": Regime.DHA,
        "RUDA": Regime.RUDA,
        "RAVI URBAN DEVELOPMENT AUTHORITY": Regime.RUDA,
        "CANTONMENT": Regime.CANTONMENT,
        "CANTONMENT BOARD": Regime.CANTONMENT,
        "CB": Regime.CANTONMENT,
        "SOCIETY": Regime.SOCIETY,
        "COOPERATIVE SOCIETY": Regime.SOCIETY,
        "REVENUE": Regime.REVENUE,
        "LAND REVENUE": Regime.REVENUE,
        "MUNICIPAL": Regime.MUNICIPAL,
        "MUNICIPALITY": Regime.MUNICIPAL,
        "TMA": Regime.MUNICIPAL,
        "MC": Regime.MUNICIPAL,
    }
    
    for alias, regime in aliases.items():
        if alias in normalized:
            return regime
    
    return Regime.UNKNOWN

