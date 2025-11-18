import os
from unittest.mock import patch, MagicMock


def make_secret_payload(value: str):
    class Payload:
        def __init__(self, v):
            self.data = v.encode("UTF-8")

    class Response:
        def __init__(self, v):
            self.payload = Payload(v)

    return Response(value)


@patch("google.cloud.secretmanager.SecretManagerServiceClient")
def test_load_google_secrets_uses_adc(mock_sm_client):
    # Setup fake client to return a secret for each call
    client_instance = MagicMock()
    client_instance.access_secret_version.return_value = make_secret_payload("testval")
    mock_sm_client.return_value = client_instance

    with patch("google.auth.default", return_value=(None, "adc-project")):
        # Ensure no env var first
        os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
        from src.config import load_google_secrets

        load_google_secrets()
        assert os.environ.get("GOOGLE_CLOUD_PROJECT") == "adc-project"
        # secrets should set env vars in a mapping; at least one of them
        assert os.environ.get("GOOGLE_API_KEY") == "testval"


@patch("google.cloud.secretmanager.SecretManagerServiceClient")
def test_load_google_secrets_falls_back_to_metadata(mock_sm_client):
    client_instance = MagicMock()
    client_instance.access_secret_version.return_value = make_secret_payload("meta-secret")
    mock_sm_client.return_value = client_instance

    with patch("google.auth.default", return_value=(None, None)):
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.text = "metadata-project"
            mock_get.return_value = mock_resp

            os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
            from src.config import load_google_secrets

            load_google_secrets()
            assert os.environ.get("GOOGLE_CLOUD_PROJECT") == "metadata-project"
            assert os.environ.get("GOOGLE_API_KEY") == "meta-secret"


@patch("google.cloud.secretmanager.SecretManagerServiceClient")
def test_load_google_secrets_metadata_failure(mock_sm_client):
    client_instance = MagicMock()
    mock_sm_client.return_value = client_instance

    with patch("google.auth.default", return_value=(None, None)):
        with patch("requests.get", side_effect=Exception("timeout")):
            os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
            from src.config import load_google_secrets

            # Should not raise
            load_google_secrets()
            assert os.environ.get("GOOGLE_CLOUD_PROJECT") is None