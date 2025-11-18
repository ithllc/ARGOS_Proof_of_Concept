"""
Configuration loader for the Mini-ARGOS POC.

This module loads environment variables for the application. It detects
if it is running in a Google Cloud environment and loads secrets from
Google Secret Manager. Otherwise, it assumes a local environment and
loads from a .env file.
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_google_secrets():
    """Loads secrets from Google Secret Manager."""
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()

        # Resolve GCP project id: prefer env var, then ADC, then metadata server
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            # Prefer Application Default Credentials (ADC)
            try:
                from google.auth import default as google_auth_default
                _, project_id = google_auth_default()
                if project_id:
                    logging.info("Determined project_id from ADC.")
            except Exception:
                project_id = None

        if not project_id:
            # Fall back to the metadata server (Cloud Run / GCE)
            try:
                import requests
                metadata_url = "http://metadata.google.internal/computeMetadata/v1/project/project-id"
                resp = requests.get(metadata_url, headers={"Metadata-Flavor": "Google"}, timeout=2)
                if resp.ok and resp.text:
                    project_id = resp.text.strip()
                    logging.info("Determined project_id from metadata server.")
            except Exception as e:
                logging.warning(f"Could not determine project_id from metadata server: {e}")

        if not project_id:
            logging.error("GOOGLE_CLOUD_PROJECT environment variable not set and could not be determined from ADC or metadata.")
            return

        # Export to env for downstream compatibility
        os.environ["GOOGLE_CLOUD_PROJECT"] = project_id

        secrets_to_load = {
            "ARGOS_GOOGLE_API_KEY": "GOOGLE_API_KEY",
            "ARGOS_REDIS_HOST": "REDIS_HOST",
            "ARGOS_REDIS_PORT": "REDIS_PORT",
            "ARGOS_TAVILY_API_KEY": "TAVILY_API_KEY",
        }

        for secret_name, env_var_name in secrets_to_load.items():
            secret_path = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            try:
                response = client.access_secret_version(request={"name": secret_path})
                secret_value = response.payload.data.decode("UTF-8")
                os.environ[env_var_name] = secret_value
                logging.info(f"Loaded secret '{secret_name}' into environment variable '{env_var_name}'.")
            except Exception as e:
                logging.warning(f"Could not load secret {secret_name}: {e}")

    except ImportError:
        logging.warning("google-cloud-secret-manager is not installed. Cannot load secrets from Google Secret Manager.")
    except Exception as e:
        logging.error(f"Failed to load secrets from Google Secret Manager: {e}", exc_info=True)

# Check if running in Google Cloud environment
if os.environ.get("K_SERVICE") or os.environ.get("FUNCTION_TARGET"):
    logging.info("Running in Google Cloud environment. Loading secrets from Secret Manager.")
    load_google_secrets()
else:
    # Local environment: load from .env file
    logging.info("Running in local environment. Loading from .env file.")
    project_root = Path(__file__).parent.parent.resolve()
    dotenv_path = project_root / '.env'

    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path)
        logging.info(f".env file loaded from {dotenv_path}")
    else:
        logging.warning(f"Warning: .env file not found at {dotenv_path}. "
                        "Application may not function correctly without required environment variables.")

