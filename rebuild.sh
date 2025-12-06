#!/bin/bash

echo "Building and deploying NYet Cooking with Redis..."

# Build and push Docker image
echo "Building Docker image..."
docker build --platform=linux/amd64 . -t tupperward/nyetcooking
echo "Pushing Docker image..."
docker push tupperward/nyetcooking

# Delete old Redis deployment if it exists
echo "Checking for old Redis deployment..."
if kubectl get deployment redis -n blog &> /dev/null; then
  echo "Deleting old Redis deployment..."
  kubectl delete deployment redis -n blog
fi

# Apply Redis configurations
echo "Applying Redis StatefulSet..."
kubectl apply -f k8s/redis.yaml
echo "Applying Redis Service..."
kubectl apply -f k8s/redis-service.yaml

# Restart the app deployment
echo "Restarting app deployment..."
kubectl rollout restart deploy -n blog nyetcooking

echo "Deployment complete! Checking status..."
kubectl get pods -n blog -l app=nyetcooking
kubectl get pods -n blog -l app=redis
kubectl get pvc -n blog
