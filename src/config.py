"""
Configuration loader for the Mini-ARGOS POC.

This module finds and loads the .env file from the project's root directory,
making environment variables available to the application. It also logs a
warning if the file is not found.
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# The root of the project is considered to be the parent of the 'src' directory
# where this file resides.
project_root = Path(__file__).parent.parent.resolve()
dotenv_path = project_root / '.env'

if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
    logging.info(f".env file loaded from {dotenv_path}")
else:
    logging.warning(f"Warning: .env file not found at {dotenv_path}. "
                    "Application may not function correctly without required environment variables.")
