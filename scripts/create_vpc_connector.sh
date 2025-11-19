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
