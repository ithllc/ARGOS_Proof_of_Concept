"""
Endpoint Verification Script
Tests that all CopilotKit and API endpoints are responding correctly.
"""

import requests

BASE_URL = "http://localhost:8000"

def test_endpoint(url, expected_status=200):
    try:
        response = requests.get(url)
        if response.status_code == expected_status:
            print(f"✓ {url} - OK")
            return True
        else:
            print(f"✗ {url} - Failed (Status: {response.status_code})")
            return False
    except Exception as e:
        print(f"✗ {url} - Error: {e}")
        return False

def test_copilotkit_endpoint(agent_name):
    url = f"{BASE_URL}/copilotkit/{agent_name}"
    return test_endpoint(url, expected_status=200)

if __name__ == "__main__":
    print("Verifying ARGOS POC Endpoints...")
    print("="*60)

    print("\nAPI Endpoints:")
    test_endpoint(f"{BASE_URL}/")
    test_endpoint(f"{BASE_URL}/status")
    test_endpoint(f"{BASE_URL}/api/papers")

    print("\nCopilotKit / AG-UI Endpoints:")
    for agent in ["coordinator", "research", "planning", "analysis"]:
        test_copilotkit_endpoint(agent)

    print("\n" + "="*60)
    print("Verification complete.")
