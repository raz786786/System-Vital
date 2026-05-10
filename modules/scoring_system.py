"""
Scoring System Module
Calculates component and overall system scores
"""

from typing import Dict
from utils.logger import setup_logger
from utils.helpers import get_tier_from_score, get_tier_color
import config

logger = setup_logger(__name__)

class ScoringSystem:
    """Calculate hardware scores and tiers"""
    
    def __init__(self):
        logger.info("Scoring System initialized")
    
    def calculate_overall_score(self, component_scores: Dict) -> Dict:
        """
        Calculate overall system score
        
        Args:
            component_scores: Dictionary of component scores
        
        Returns:
            Dict: Overall score and analysis
        """
        logger.info("Calculating overall system score...")
        
        # Extract scores
        cpu_score = component_scores.get('cpu', {}).get('score', 50)
        gpu_score = component_scores.get('gpu', {}).get('score', 50)
        ram_score = component_scores.get('ram', {}).get('score', 50)
        storage_score = component_scores.get('storage', {}).get('score', 50)
        
        # Calculate weighted score
        weighted_score = (
            cpu_score * config.SCORE_WEIGHTS['cpu'] +
            gpu_score * config.SCORE_WEIGHTS['gpu'] +
            ram_score * config.SCORE_WEIGHTS['ram'] +
            storage_score * config.SCORE_WEIGHTS['storage']
        )
        
        # Calculate balance penalty
        scores = [cpu_score, gpu_score, ram_score, storage_score]
        score_range = max(scores) - min(scores)
        balance_penalty = min(score_range / 2, 20)  # Max 20 point penalty
        
        # Final score
        final_score = max(0, min(100, weighted_score - balance_penalty))
        
        # Determine tier
        tier = get_tier_from_score(int(final_score))
        
        # Identify bottleneck
        bottleneck = self._identify_bottleneck(component_scores)
        
        result = {
            'overall_score': int(final_score),
            'tier': tier,
            'color': get_tier_color(tier),
            'weighted_score': int(weighted_score),
            'balance_penalty': int(balance_penalty),
            'bottleneck': bottleneck,
            'component_scores': {
                'cpu': cpu_score,
                'gpu': gpu_score,
                'ram': ram_score,
                'storage': storage_score,
            }
        }
        
        logger.info(f"Overall score calculated: {final_score} ({tier})")
        return result
    
    def score_cpu(self, cpu_info: Dict, comparison_data: Dict = None) -> Dict:
        """
        Score CPU performance
        
        Args:
            cpu_info: CPU information
            comparison_data: Online comparison data
        
        Returns:
            Dict: CPU score and tier
        """
        logger.info("Scoring CPU...")
        
        # Base score from comparison data
        if comparison_data:
            score = comparison_data.get('percentile', 50)
        else:
            # Fallback scoring based on specs
            cores = cpu_info.get('cores', 4)
            threads = cpu_info.get('threads', 4)
            freq = cpu_info.get('max_frequency', 2000)
            
            # Simple heuristic
            core_score = min(cores * 5, 40)  # Up to 40 points for cores
            thread_score = min(threads * 2.5, 30)  # Up to 30 points for threads
            freq_score = min((freq / 100), 30)  # Up to 30 points for frequency
            
            score = core_score + thread_score + freq_score
        
        tier = get_tier_from_score(int(score))
        
        return {
            'score': int(score),
            'tier': tier,
            'color': get_tier_color(tier),
            'component': 'CPU'
        }
    
    def score_gpu(self, gpu_info: Dict, comparison_data: Dict = None) -> Dict:
        """
        Score GPU performance
        
        Args:
            gpu_info: GPU information
            comparison_data: Online comparison data
        
        Returns:
            Dict: GPU score and tier
        """
        logger.info("Scoring GPU...")
        
        # Base score from comparison data
        if comparison_data:
            score = comparison_data.get('percentile', 50)
        else:
            # Fallback scoring based on VRAM
            vram = gpu_info.get('vram', 0)
            vram_gb = vram / (1024 ** 3) if vram else 0
            
            # Simple heuristic based on VRAM
            if vram_gb >= 12:
                score = 90
            elif vram_gb >= 8:
                score = 75
            elif vram_gb >= 6:
                score = 60
            elif vram_gb >= 4:
                score = 45
            else:
                score = 30
        
        tier = get_tier_from_score(int(score))
        
        return {
            'score': int(score),
            'tier': tier,
            'color': get_tier_color(tier),
            'component': 'GPU'
        }
    
    def score_ram(self, ram_info: Dict) -> Dict:
        """
        Score RAM configuration
        
        Args:
            ram_info: RAM information
        
        Returns:
            Dict: RAM score and tier
        """
        logger.info("Scoring RAM...")
        
        total_gb = ram_info.get('total', 0) / (1024 ** 3)
        modules = ram_info.get('modules', [])
        
        # Score based on capacity
        if total_gb >= 32:
            capacity_score = 90
        elif total_gb >= 16:
            capacity_score = 75
        elif total_gb >= 8:
            capacity_score = 55
        else:
            capacity_score = 30
        
        # Bonus for dual/quad channel
        if len(modules) in [2, 4]:
            capacity_score += 5
        
        # Check speed (if available)
        if modules:
            speeds = [m.get('speed', 0) for m in modules]
            avg_speed = sum(speeds) / len(speeds) if speeds else 0
            
            if avg_speed >= 3200:
                speed_bonus = 5
            elif avg_speed >= 2666:
                speed_bonus = 3
            else:
                speed_bonus = 0
            
            capacity_score += speed_bonus
        
        score = min(100, capacity_score)
        tier = get_tier_from_score(int(score))
        
        return {
            'score': int(score),
            'tier': tier,
            'color': get_tier_color(tier),
            'component': 'RAM'
        }
    
    def score_storage(self, storage_info: list) -> Dict:
        """
        Score storage configuration
        
        Args:
            storage_info: List of storage devices
        
        Returns:
            Dict: Storage score and tier
        """
        logger.info("Scoring storage...")
        
        if not storage_info:
            return {'score': 0, 'tier': 'Bad', 'color': get_tier_color('Bad')}
        
        # Check for SSD (simplified - would check filesystem type or device type)
        total_capacity = sum(d.get('total', 0) for d in storage_info)
        total_gb = total_capacity / (1024 ** 3)
        
        # Score based on capacity
        if total_gb >= 1000:
            score = 85
        elif total_gb >= 500:
            score = 70
        elif total_gb >= 250:
            score = 55
        else:
            score = 40
        
        # Check health
        for device in storage_info:
            if device.get('smart_health') == 'FAIL':
                score -= 30  # Major penalty for failing drive
        
        score = max(0, min(100, score))
        tier = get_tier_from_score(int(score))
        
        return {
            'score': int(score),
            'tier': tier,
            'color': get_tier_color(tier),
            'component': 'Storage'
        }
    
    def _identify_bottleneck(self, component_scores: Dict) -> Dict:
        """Identify system bottleneck"""
        scores = {
            'CPU': component_scores.get('cpu', {}).get('score', 50),
            'GPU': component_scores.get('gpu', {}).get('score', 50),
            'RAM': component_scores.get('ram', {}).get('score', 50),
            'Storage': component_scores.get('storage', {}).get('score', 50),
        }
        
        weakest = min(scores, key=scores.get)
        strongest = max(scores, key=scores.get)
        
        gap = scores[strongest] - scores[weakest]
        
        if gap > 30:
            return {
                'component': weakest,
                'score': scores[weakest],
                'gap': gap,
                'is_bottleneck': True,
                'recommendation': f'{weakest} is significantly weaker than {strongest}'
            }
        else:
            return {
                'is_bottleneck': False,
                'recommendation': 'System is well-balanced'
            }

# Convenience function
def calculate_system_score(hardware_info: Dict, comparison_data: Dict = None) -> Dict:
    """
    Convenience function to calculate system score
    
    Returns:
        Dict: Complete scoring results
    """
    scorer = ScoringSystem()
    
    component_scores = {
        'cpu': scorer.score_cpu(hardware_info.get('cpu', {}), comparison_data.get('cpu') if comparison_data else None),
        'gpu': scorer.score_gpu(hardware_info.get('gpu', [{}])[0] if hardware_info.get('gpu') else {}, 
                               comparison_data.get('gpu') if comparison_data else None),
        'ram': scorer.score_ram(hardware_info.get('ram', {})),
        'storage': scorer.score_storage(hardware_info.get('storage', [])),
    }
    
    overall = scorer.calculate_overall_score(component_scores)
    
    return {
        'overall': overall,
        'components': component_scores
    }
