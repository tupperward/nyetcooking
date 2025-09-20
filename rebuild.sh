#!/bin/bash

echo "Building and deploying NYet Cooking with Redis..."

# Build and push Docker image
echo "Building Docker image..."
docker build --platform=linux/amd64 . -t tupperward/nyetcooking
echo "Pushing Docker image..."
docker push tupperward/nyetcooking

# Deploy Redis if not already deployed
echo "Deploying Redis..."
kubectl apply -f k8s-redis.yaml

# Wait for Redis to be ready
echo "Waiting for Redis to be ready..."
kubectl wait --for=condition=available --timeout=60s deployment/redis -n blog

# Update your app deployment with Redis environment variables
echo "Updating app deployment..."
kubectl patch deployment nyetcooking -n blog -p '{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "nyetcooking",
          "env": [
            {"name": "REDIS_HOST", "value": "redis-service"},
            {"name": "REDIS_PORT", "value": "6379"}
          ]
        }]
      }
    }
  }
}'

# Restart the app deployment
echo "Restarting app deployment..."
kubectl rollout restart deploy -n blog nyetcooking

echo "Deployment complete! Checking status..."
kubectl get pods -n blog -l app=redis
kubectl get pods -n blog -l app=nyetcooking
