"""
Helper utilities for Hardware Diagnostic Tool
"""

import re
import hashlib
from typing import Optional

def clean_component_name(name: str) -> str:
    """
    Clean and normalize component names for comparison
    
    Args:
        name: Raw component name
    
    Returns:
        str: Cleaned component name
    """
    if not name:
        return ""
    
    # Remove extra whitespace
    name = " ".join(name.split())
    
    # Remove common suffixes/prefixes
    removals = [
        r'\(R\)', r'\(TM\)', r'\(C\)',
        r'@.*',  # Remove @ and everything after (frequencies)
        r'\s+\d+\.\d+GHz',  # Remove frequency specs
        r'\s+with.*',  # Remove "with Radeon Graphics" etc
    ]
    
    for pattern in removals:
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)
    
    return name.strip()

def format_bytes(bytes_value: int, precision: int = 2) -> str:
    """
    Format bytes to human-readable format
    
    Args:
        bytes_value: Number of bytes
        precision: Decimal precision
    
    Returns:
        str: Formatted string (e.g., "16.0 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.{precision}f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.{precision}f} PB"

def format_frequency(mhz: float) -> str:
    """
    Format frequency in MHz to GHz if appropriate
    
    Args:
        mhz: Frequency in MHz
    
    Returns:
        str: Formatted frequency
    """
    if mhz >= 1000:
        return f"{mhz / 1000:.2f} GHz"
    return f"{mhz:.0f} MHz"

def calculate_percentile(value: float, min_val: float, max_val: float) -> int:
    """
    Calculate percentile of a value within a range
    
    Args:
        value: Current value
        min_val: Minimum value in range
        max_val: Maximum value in range
    
    Returns:
        int: Percentile (0-100)
    """
    if max_val == min_val:
        return 50
    
    percentile = ((value - min_val) / (max_val - min_val)) * 100
    return max(0, min(100, int(percentile)))

def generate_hash(text: str) -> str:
    """
    Generate MD5 hash of text
    
    Args:
        text: Input text
    
    Returns:
        str: MD5 hash
    """
    return hashlib.md5(text.encode()).hexdigest()

def safe_int(value, default: int = 0) -> int:
    """
    Safely convert value to int
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
    
    Returns:
        int: Converted value or default
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value, default: float = 0.0) -> float:
    """
    Safely convert value to float
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
    
    Returns:
        float: Converted value or default
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate string to maximum length
    
    Args:
        text: Input text
        max_length: Maximum length
        suffix: Suffix to add if truncated
    
    Returns:
        str: Truncated string
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def get_tier_from_score(score: int) -> str:
    """
    Get tier classification from score
    
    Args:
        score: Score (0-100)
    
    Returns:
        str: Tier name (Best, Average, Bad)
    """
    if score >= 90:
        return "Best"
    elif score >= 60:
        return "Average"
    else:
        return "Bad"

def get_tier_color(tier: str) -> str:
    """
    Get color for tier
    
    Args:
        tier: Tier name
    
    Returns:
        str: Hex color code
    """
    colors = {
        "Best": "#4CAF50",      # Green
        "Average": "#FF9800",   # Orange
        "Bad": "#F44336"        # Red
    }
    return colors.get(tier, "#9E9E9E")  # Gray as default
