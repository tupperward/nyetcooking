#!/bin/bash

echo "Building and deploying NYet Cooking with Redis..."

# Build and push Docker image
echo "Building Docker image..."
docker build --platform=linux/amd64 . -t tupperward/nyetcooking
echo "Pushing Docker image..."
docker push tupperward/nyetcooking


# Restart the app deployment
echo "Restarting app deployment..."
kubectl rollout restart deploy -n blog nyetcooking

echo "Deployment complete! Checking status..."
kubectl get pods -n blog -l app=nyetcooking
