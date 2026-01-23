#!/usr/bin/env python3
"""LocalAgent server implementation."""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Import VERSION from package init
from . import VERSION

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LocalAgentServer:
    """Main server class for LocalAgent."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the LocalAgent server.
        
        Args:
            config_path: Optional path to configuration file
        """
        self.version = VERSION
        self.config_path = config_path
        self.config = self._load_config()
        
        logger.info(f"LocalAgent Server v{self.version} initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or use defaults.
        
        Returns:
            Configuration dictionary
        """
        default_config = {
            "host": "localhost",
            "port": 8080,
            "debug": False,
            "max_tasks_per_request": 3,
            "max_lines_per_task": 120
        }
        
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
                logger.info(f"Configuration loaded from {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config from {self.config_path}: {e}")
        
        return default_config
    
    def get_version(self) -> str:
        """Get the current version.
        
        Returns:
            Version string
        """
        return self.version
    
    def start(self):
        """Start the LocalAgent server."""
        host = self.config["host"]
        port = self.config["port"]
        
        logger.info(f"Starting LocalAgent Server v{self.version}")
        logger.info(f"Server configuration: {host}:{port}")
        
        # TODO: Implement actual server startup logic
        print(f"LocalAgent Server v{self.version} would start on {host}:{port}")

def main():
    """Main entry point for the server."""
    import argparse
    
    parser = argparse.ArgumentParser(description=f"LocalAgent Server v{VERSION}")
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"LocalAgent Server v{VERSION}"
    )
    
    args = parser.parse_args()
    
    try:
        server = LocalAgentServer(config_path=args.config)
        server.start()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
