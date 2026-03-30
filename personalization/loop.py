"""
Personalization Loop - Continuous learning from user interactions
SILS v1 - Shadow Intelligence Layer
"""

import os
import json
import numpy as np
import torch
from typing import Optional, Dict
from tone.tone_analysis import ToneAnalyzer
from core.app_paths import get_personalization_path


class PersonalizationLoop:
    """
    Maintains and updates per-user style embeddings using exponential moving average.
    
    Features:
    - Per-user style embedding (64-dim)
    - EMA updates (α = 0.85)
    - Persistent storage in Shadow's app-data directory
    - Never overwrites base LM weights
    """
    
    def __init__(self, config, user_id: str = "default"):
        self.config = config
        self.user_id = user_id
        self.ema_alpha = config["personalization"]["ema_alpha"]
        self.style_dim = config["personalization"]["style_dim"]
        
        # Initialize tone analyzer
        self.tone_analyzer = ToneAnalyzer()
        
        # Storage path
        self.profile_path = get_personalization_path(user_id)
        self.shadow_dir = self.profile_path.parent
        
        # User profile
        self.user_profile = self._load_profile()
    
    def _load_profile(self) -> Dict:
        """Load or initialize user profile."""
        if self.profile_path.exists():
            with open(self.profile_path, 'r') as f:
                profile = json.load(f)
            
            # Convert style embedding back to numpy
            profile['style_embedding'] = np.array(profile['style_embedding'], dtype=np.float32)
            
            return profile
        else:
            # Initialize blank profile
            return {
                'user_id': self.user_id,
                'style_embedding': np.zeros(self.style_dim, dtype=np.float32),
                'message_count': 0,
                'preferences': {
                    'warmth': 0.0,
                    'directness': 0.0,
                    'profanity': 0.0
                }
            }
    
    def _save_profile(self):
        """Save user profile to disk."""
        # Ensure directory exists
        self.shadow_dir.mkdir(parents=True, exist_ok=True)
        
        # Convert numpy array to list for JSON
        profile_to_save = self.user_profile.copy()
        profile_to_save['style_embedding'] = self.user_profile['style_embedding'].tolist()

        with open(self.profile_path, 'w') as f:
            json.dump(profile_to_save, f, indent=2)

        # Secure permissions
        if os.name != "nt":
            os.chmod(self.profile_path, 0o600)
    
    def update(self, user_message: str):
        """
        Update user style embedding based on new message.
        
        Args:
            user_message: User's input text
        """
        # Extract current style from message
        current_style = self.tone_analyzer.analyze(user_message)
        
        # EMA update
        old_style = self.user_profile['style_embedding']
        new_style = self.ema_alpha * old_style + (1 - self.ema_alpha) * current_style
        
        self.user_profile['style_embedding'] = new_style
        self.user_profile['message_count'] += 1
        
        # Update preference summary
        style_summary = self.tone_analyzer.get_style_summary(user_message)
        for key in ['warmth', 'directness', 'profanity']:
            if key in style_summary:
                old_pref = self.user_profile['preferences'][key]
                self.user_profile['preferences'][key] = (
                    self.ema_alpha * old_pref + (1 - self.ema_alpha) * style_summary[key]
                )
        
        # Save to disk
        self._save_profile()
    
    def get_style_embedding(self) -> torch.Tensor:
        """
        Get current user style embedding as PyTorch tensor.
        
        Returns:
            style_embedding: (1, 64) tensor
        """
        embedding = torch.from_numpy(self.user_profile['style_embedding']).float()
        return embedding.unsqueeze(0)  # Add batch dimension
    
    def get_style_numpy(self) -> np.ndarray:
        """
        Get current user style embedding as numpy array.
        
        Returns:
            style_embedding: (64,) numpy array
        """
        return self.user_profile['style_embedding'].copy()
    
    def reset(self):
        """Reset user profile to blank state."""
        self.user_profile = {
            'user_id': self.user_id,
            'style_embedding': np.zeros(self.style_dim, dtype=np.float32),
            'message_count': 0,
            'preferences': {
                'warmth': 0.0,
                'directness': 0.0,
                'profanity': 0.0
            }
        }
        self._save_profile()
    
    def get_preferences(self) -> Dict[str, float]:
        """Get user's style preferences."""
        return self.user_profile['preferences'].copy()
    
    def get_stats(self) -> Dict:
        """Get personalization statistics."""
        return {
            'user_id': self.user_id,
            'message_count': self.user_profile['message_count'],
            'style_norm': float(np.linalg.norm(self.user_profile['style_embedding'])),
            'preferences': self.get_preferences()
        }
    
    def is_initialized(self) -> bool:
        """Check if user has any personalization data."""
        return self.user_profile['message_count'] > 0
    
    def export_profile(self, path: str):
        """Export user profile to specified path."""
        profile_to_save = self.user_profile.copy()
        profile_to_save['style_embedding'] = self.user_profile['style_embedding'].tolist()
        
        with open(path, 'w') as f:
            json.dump(profile_to_save, f, indent=2)
    
    def import_profile(self, path: str):
        """Import user profile from specified path."""
        with open(path, 'r') as f:
            profile = json.load(f)
        
        profile['style_embedding'] = np.array(profile['style_embedding'], dtype=np.float32)
        self.user_profile = profile
        self._save_profile()
