docker build --platform=linux/amd64 . -t tupperward/nyetcooking
docker push tupperward/nyetcooking
kubectl rollout restart deploy -n blog nyetcooking
