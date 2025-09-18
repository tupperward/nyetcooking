docker build . -t tupperward/nyetcooking
docker push tupperward/nyetcooking
kubectl rollout restart deploy -n blog nyetcooking
