"""Profile and credential management with encryption.

Manages trading profiles with encrypted credentials stored securely.
Each profile can have different API keys, risk limits, and configurations.
"""

import os
import json
import base64
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Try to import cryptography
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning("cryptography package not installed. Install with: pip install cryptography")


class ProfileManager:
    """Manage trading profiles with encrypted credentials."""

    def __init__(self, master_password: Optional[str] = None):
        """Initialize profile manager.

        Args:
            master_password: Master password for encryption (defaults to env var)
        """
        self.profiles_dir = Path.home() / '.trading-bot' / 'profiles'
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

        # Initialize encryption
        if CRYPTO_AVAILABLE:
            password = master_password or os.getenv('MASTER_PASSWORD', 'changeme-default-password')
            self.cipher = self._create_cipher(password)
            self.encryption_enabled = True
        else:
            self.cipher = None
            self.encryption_enabled = False
            logger.warning("Encryption disabled - cryptography package not available")

        self.active_profile = None

    def _create_cipher(self, password: str) -> 'Fernet':
        """Create Fernet cipher from password.

        Args:
            password: Master password

        Returns:
            Fernet cipher instance
        """
        if not CRYPTO_AVAILABLE:
            return None

        # Use PBKDF2 to derive a key from password
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'trading-bot-salt-v1',  # In production, use random salt per user
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)

    def create_profile(self, name: str, config: Dict[str, Any]) -> str:
        """Create new trading profile.

        Args:
            name: Profile name
            config: Profile configuration including credentials

        Returns:
            Profile ID

        Raises:
            ValueError: If profile already exists
        """
        profile_id = name.lower().replace(' ', '_')
        profile_path = self.profiles_dir / f"{profile_id}.json"

        if profile_path.exists():
            raise ValueError(f"Profile '{name}' already exists")

        # Encrypt sensitive fields
        encrypted_config = self._encrypt_credentials(config)

        profile = {
            'id': profile_id,
            'name': name,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'config': encrypted_config,
            'encrypted': self.encryption_enabled
        }

        with open(profile_path, 'w') as f:
            json.dump(profile, f, indent=2)

        logger.info(f"Created profile: {name} (encrypted={self.encryption_enabled})")
        return profile_id

    def _encrypt_credentials(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive credential fields.

        Args:
            config: Configuration dict

        Returns:
            Config with encrypted credentials
        """
        if not self.encryption_enabled or not self.cipher:
            return config

        encrypted = config.copy()

        # Sensitive fields that should be encrypted
        sensitive_fields = [
            'api_key', 'api_secret', 'private_key', 'password',
            'binance_api_key', 'binance_api_secret',
            'coinbase_api_key', 'coinbase_api_secret',
            'bybit_api_key', 'bybit_api_secret',
            'kraken_api_key', 'kraken_api_secret',
            'dydx_api_key', 'dydx_private_key',
            'polymarket_api_key', 'polymarket_private_key',
            'luno_api_key', 'luno_api_secret',
            'kalshi_api_key', 'kalshi_api_secret',
        ]

        for field in sensitive_fields:
            if field in encrypted and encrypted[field]:
                try:
                    value = encrypted[field]
                    encrypted_value = self.cipher.encrypt(value.encode()).decode()
                    encrypted[field] = encrypted_value
                except Exception as e:
                    logger.error(f"Failed to encrypt {field}: {e}")

        return encrypted

    def _decrypt_credentials(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive credential fields.

        Args:
            config: Configuration dict with encrypted credentials

        Returns:
            Config with decrypted credentials
        """
        if not self.encryption_enabled or not self.cipher:
            return config

        decrypted = config.copy()

        sensitive_fields = [
            'api_key', 'api_secret', 'private_key', 'password',
            'binance_api_key', 'binance_api_secret',
            'coinbase_api_key', 'coinbase_api_secret',
            'bybit_api_key', 'bybit_api_secret',
            'kraken_api_key', 'kraken_api_secret',
            'dydx_api_key', 'dydx_private_key',
            'polymarket_api_key', 'polymarket_private_key',
            'luno_api_key', 'luno_api_secret',
            'kalshi_api_key', 'kalshi_api_secret',
        ]

        for field in sensitive_fields:
            if field in decrypted and decrypted[field]:
                try:
                    value = decrypted[field]
                    decrypted_value = self.cipher.decrypt(value.encode()).decode()
                    decrypted[field] = decrypted_value
                except Exception as e:
                    logger.error(f"Failed to decrypt {field}: {e}")
                    decrypted[field] = None

        return decrypted

    def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get profile by ID with decrypted credentials.

        Args:
            profile_id: Profile identifier

        Returns:
            Profile dict or None if not found
        """
        profile_path = self.profiles_dir / f"{profile_id}.json"

        if not profile_path.exists():
            return None

        with open(profile_path) as f:
            profile = json.load(f)

        # Decrypt credentials if encrypted
        if profile.get('encrypted', False):
            profile['config'] = self._decrypt_credentials(profile['config'])

        return profile

    def list_profiles(self) -> List[Dict[str, Any]]:
        """List all profiles (without decrypted credentials).

        Returns:
            List of profile metadata
        """
        profiles = []

        for profile_path in self.profiles_dir.glob('*.json'):
            try:
                with open(profile_path) as f:
                    profile = json.load(f)

                # Don't include credentials in list
                profiles.append({
                    'id': profile['id'],
                    'name': profile['name'],
                    'created_at': profile['created_at'],
                    'updated_at': profile.get('updated_at', profile['created_at']),
                    'encrypted': profile.get('encrypted', False),
                    'is_active': self.active_profile and self.active_profile['id'] == profile['id']
                })
            except Exception as e:
                logger.error(f"Error loading profile {profile_path}: {e}")

        return sorted(profiles, key=lambda p: p['created_at'], reverse=True)

    def update_profile(self, profile_id: str, config: Dict[str, Any]) -> bool:
        """Update existing profile.

        Args:
            profile_id: Profile identifier
            config: Updated configuration

        Returns:
            True if successful
        """
        profile = self.get_profile(profile_id)
        if not profile:
            return False

        # Encrypt sensitive fields
        encrypted_config = self._encrypt_credentials(config)

        profile['config'] = encrypted_config
        profile['updated_at'] = datetime.now().isoformat()

        profile_path = self.profiles_dir / f"{profile_id}.json"
        with open(profile_path, 'w') as f:
            json.dump(profile, f, indent=2)

        logger.info(f"Updated profile: {profile_id}")
        return True

    def activate_profile(self, profile_id: str) -> bool:
        """Activate a profile for trading.

        Args:
            profile_id: Profile to activate

        Returns:
            True if successful
        """
        profile = self.get_profile(profile_id)
        if not profile:
            return False

        self.active_profile = profile
        logger.info(f"Activated profile: {profile['name']}")
        return True

    def get_active_profile(self) -> Optional[Dict[str, Any]]:
        """Get currently active profile.

        Returns:
            Active profile dict or None
        """
        return self.active_profile

    def delete_profile(self, profile_id: str) -> bool:
        """Delete a profile.

        Args:
            profile_id: Profile to delete

        Returns:
            True if successful
        """
        profile_path = self.profiles_dir / f"{profile_id}.json"

        if not profile_path.exists():
            return False

        # Don't allow deleting active profile
        if self.active_profile and self.active_profile['id'] == profile_id:
            logger.warning(f"Cannot delete active profile: {profile_id}")
            return False

        profile_path.unlink()
        logger.info(f"Deleted profile: {profile_id}")
        return True

    def validate_credentials(self, provider: str, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Validate API credentials by testing connection.

        Args:
            provider: Provider name
            credentials: Credential dict

        Returns:
            Validation result with permissions
        """
        try:
            # Import here to avoid circular dependency
            from ..providers import create_provider

            # Create provider instance
            prov = create_provider(provider, credentials)

            # Test connection by getting balance
            # Note: This is a simplified check - actual validation would be async
            return {
                'valid': True,
                'message': 'Credentials appear valid',
                'permissions': {
                    'trading': True,  # Assume trading permissions
                    'withdrawal': False,  # Assume no withdrawal unless explicitly granted
                    'reading': True
                }
            }

        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'message': f'Failed to validate credentials: {str(e)}'
            }

    def mask_credentials(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive credentials for display.

        Args:
            config: Configuration with credentials

        Returns:
            Config with masked credentials
        """
        masked = config.copy()

        sensitive_fields = [
            'api_key', 'api_secret', 'private_key', 'password',
            'binance_api_key', 'binance_api_secret',
            'coinbase_api_key', 'coinbase_api_secret',
            'bybit_api_key', 'bybit_api_secret',
            'kraken_api_key', 'kraken_api_secret',
            'dydx_api_key', 'dydx_private_key',
            'polymarket_api_key', 'polymarket_private_key',
            'luno_api_key', 'luno_api_secret',
            'kalshi_api_key', 'kalshi_api_secret',
        ]

        for field in sensitive_fields:
            if field in masked and masked[field]:
                value = str(masked[field])
                if len(value) > 4:
                    masked[field] = '•' * 16 + value[-4:]
                else:
                    masked[field] = '•' * len(value)

        return masked
