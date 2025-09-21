"""iCloud authentication handling."""

import logging
from typing import Optional
from pyicloud import PyiCloudService

logger = logging.getLogger(__name__)

class ICloudAuth:
    """Handle iCloud authentication and session management."""
    
    def __init__(self):
        """Initialize iCloud authentication handler."""
        self.api: Optional[PyiCloudService] = None
    
    def authenticate(self, apple_id: str, password: str) -> PyiCloudService:
        """Authenticate with iCloud.
        
        Args:
            apple_id: Apple ID (email)
            password: iCloud password
            
        Returns:
            PyiCloudService: Authenticated iCloud service instance
            
        Raises:
            Exception: If authentication fails
        """
        try:
            logger.info(f"Authenticating with iCloud as {apple_id}")
            self.api = PyiCloudService(apple_id, password)
            
            if self.api.requires_2fa:
                logger.info("Two-factor authentication required")
                code = input("Enter the code you received: ")
                result = self.api.validate_2fa_code(code)
                logger.debug(f"2FA validation result: {result}")
            
            logger.info("Successfully authenticated with iCloud")
            return self.api
            
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise
    
    def check_session(self) -> bool:
        """Check if the current session is valid.
        
        Returns:
            bool: True if session is valid, False otherwise
        """
        if not self.api:
            return False
            
        try:
            # Try to access photos to verify session
            _ = self.api.photos.all
            return True
        except Exception:
            logger.warning("iCloud session expired or invalid")
            return False
    
    def logout(self) -> None:
        """Log out from iCloud and clean up session."""
        if self.api:
            try:
                # PyiCloud doesn't have an explicit logout method,
                # but we can clean up our reference
                self.api = None
                logger.info("Logged out from iCloud")
            except Exception as e:
                logger.error(f"Error during logout: {str(e)}")