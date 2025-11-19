# Create Missing VPC Connector

## 1. Issue Analysis

### Symptoms
The deployment fails with the error:
`VPC connector projects/argos-proof-of-concept/locations/us-central1/connectors/argos-pos-vpc-connector does not exist, or Cloud Run does not have permission to use it.`

### Root Cause
The `cloudbuild.yaml` file was updated to use a specific VPC connector (`argos-pos-vpc-connector`), but this resource has not been created in the Google Cloud project. The Cloud Run service requires this connector to bridge the serverless environment with the VPC network (to access Redis/Memorystore).

## 2. Solution

Create the missing Serverless VPC Access Connector in the `us-central1` region.

## 3. Technical Plan

### Step 1: Create Creation Script
Create a shell script `scripts/create_vpc_connector.sh` that performs the following:
1.  Enables the `vpcaccess.googleapis.com` API (idempotent).
2.  Creates the connector named `argos-pos-vpc-connector` in region `us-central1`.
3.  Attaches it to the `default` network.
4.  Uses the IP range `10.8.0.0/28` (standard range for connectors, ensuring no overlap with default auto-subnets).

### Step 2: Execute Script
Run the script to provision the infrastructure.

## 4. Coding Agent Prompts

### Prompt 1: Create and Run Infrastructure Script

```text
You need to create a script to provision the missing VPC connector.

1.  Create a new file `scripts/create_vpc_connector.sh` with the following content:
    ```bash
    #!/bin/bash
    set -e

    echo "Enabling VPC Access API..."
    gcloud services enable vpcaccess.googleapis.com

    echo "Creating VPC Access Connector 'argos-pos-vpc-connector'..."
    # Check if it exists first to avoid error
    if gcloud compute networks vpc-access connectors list --region=us-central1 | grep -q "argos-pos-vpc-connector"; then
        echo "Connector already exists."
    else
        gcloud compute networks vpc-access connectors create argos-pos-vpc-connector \
            --region us-central1 \
            --network default \
            --range 10.8.0.0/28
        echo "Connector created successfully."
    fi
    ```
2.  Make the script executable: `chmod +x scripts/create_vpc_connector.sh`.
3.  Run the script in the terminal: `./scripts/create_vpc_connector.sh`.
```
