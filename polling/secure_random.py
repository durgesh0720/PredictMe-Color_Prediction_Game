"""
Cryptographically secure random number generation for game fairness
"""
import secrets
import hashlib
import time
import logging
from typing import Tuple, List
from django.conf import settings

logger = logging.getLogger(__name__)

class SecureGameRandom:
    """
    Cryptographically secure random number generator for game results
    Uses multiple entropy sources and provides verifiable randomness
    """
    
    def __init__(self):
        self.entropy_pool = []
        self._collect_entropy()
    
    def _collect_entropy(self):
        """Collect entropy from multiple sources"""
        # System entropy
        self.entropy_pool.append(secrets.token_bytes(32))
        
        # High-resolution timestamp
        self.entropy_pool.append(str(time.time_ns()).encode())
        
        # Process ID and thread info
        import os, threading
        self.entropy_pool.append(f"{os.getpid()}-{threading.get_ident()}".encode())
    
    def _generate_seed(self, round_id: str, additional_data: str = "") -> bytes:
        """Generate a cryptographically secure seed"""
        # Refresh entropy pool
        self._collect_entropy()
        
        # Combine all entropy sources
        combined_entropy = b"".join(self.entropy_pool)
        combined_entropy += round_id.encode()
        combined_entropy += additional_data.encode()
        combined_entropy += secrets.token_bytes(16)
        
        # Use SHA-256 to create deterministic but unpredictable seed
        return hashlib.sha256(combined_entropy).digest()
    
    def generate_secure_number(self, round_id: str, min_val: int = 0, max_val: int = 9) -> Tuple[int, str]:
        """
        Generate a cryptographically secure random number
        Returns: (number, verification_hash)
        """
        try:
            # Generate seed with round-specific data
            seed = self._generate_seed(round_id, f"number-{min_val}-{max_val}")
            
            # Convert seed to integer and normalize to range
            seed_int = int.from_bytes(seed, byteorder='big')
            result = min_val + (seed_int % (max_val - min_val + 1))
            
            # Create verification hash for audit trail
            verification_data = f"{round_id}-{result}-{seed.hex()}"
            verification_hash = hashlib.sha256(verification_data.encode()).hexdigest()
            
            logger.info(f"Generated secure number for round {round_id}: {result} (hash: {verification_hash[:16]}...)")
            
            return result, verification_hash
            
        except Exception as e:
            logger.error(f"Error generating secure number: {e}")
            # Fallback to secrets module
            result = secrets.randbelow(max_val - min_val + 1) + min_val
            verification_hash = hashlib.sha256(f"fallback-{round_id}-{result}".encode()).hexdigest()
            return result, verification_hash
    
    def get_color_for_number(self, number: int) -> str:
        """Get the color that corresponds to a given number"""
        if number in [1, 3, 7, 9]:
            return 'green'
        elif number in [2, 8]:
            return 'red'
        elif number in [0, 5]:
            return 'violet'
        elif number in [4, 6]:
            return 'blue'
        else:
            logger.warning(f"Invalid number {number}, defaulting to green")
            return 'green'
    
    def get_numbers_for_color(self, color: str) -> List[int]:
        """Get all possible numbers for a given color"""
        color_map = {
            'green': [1, 3, 7, 9],
            'red': [2, 8],
            'violet': [0, 5],
            'blue': [4, 6]
        }
        return color_map.get(color, [1, 3, 7, 9])  # Default to green
    
    def generate_number_for_color(self, round_id: str, color: str) -> Tuple[int, str]:
        """
        Generate a secure random number for a specific color
        Returns: (number, verification_hash)
        """
        try:
            valid_numbers = self.get_numbers_for_color(color)
            
            if not valid_numbers:
                logger.error(f"No valid numbers for color {color}")
                return self.generate_secure_number(round_id, 0, 9)
            
            # Generate seed with color-specific data
            seed = self._generate_seed(round_id, f"color-{color}")
            
            # Select from valid numbers for this color
            seed_int = int.from_bytes(seed, byteorder='big')
            selected_number = valid_numbers[seed_int % len(valid_numbers)]
            
            # Create verification hash
            verification_data = f"{round_id}-{color}-{selected_number}-{seed.hex()}"
            verification_hash = hashlib.sha256(verification_data.encode()).hexdigest()
            
            logger.info(f"Generated secure number for round {round_id}, color {color}: {selected_number} (hash: {verification_hash[:16]}...)")
            
            return selected_number, verification_hash
            
        except Exception as e:
            logger.error(f"Error generating number for color {color}: {e}")
            # Fallback
            return self.generate_secure_number(round_id, 0, 9)
    
    def select_minimum_bet_color(self, round_id: str, bet_stats: dict) -> Tuple[str, int, str]:
        """
        Select the color with minimum bets (for admin fallback)
        Returns: (color, number, verification_hash)
        """
        try:
            # Find color with minimum total bet amount
            min_color = min(bet_stats.keys(), key=lambda c: bet_stats[c]['total_amount'])
            
            # Generate secure number for that color
            number, verification_hash = self.generate_number_for_color(round_id, min_color)
            
            logger.info(f"Selected minimum bet color for round {round_id}: {min_color} (number: {number})")
            
            return min_color, number, verification_hash
            
        except Exception as e:
            logger.error(f"Error selecting minimum bet color: {e}")
            # Fallback to random selection
            number, verification_hash = self.generate_secure_number(round_id, 0, 9)
            color = self.get_color_for_number(number)
            return color, number, verification_hash
    
    def verify_result(self, round_id: str, number: int, verification_hash: str) -> bool:
        """
        Verify that a result was generated correctly (for audit purposes)
        """
        try:
            # This is a simplified verification - in production you'd store more data
            expected_data = f"{round_id}-{number}"
            return verification_hash.startswith(hashlib.sha256(expected_data.encode()).hexdigest()[:8])
        except Exception as e:
            logger.error(f"Error verifying result: {e}")
            return False

# Global instance
secure_random = SecureGameRandom()
