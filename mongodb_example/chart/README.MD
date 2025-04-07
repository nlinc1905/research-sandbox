# MongoDB Example

Update the secret values for username/password.

```bash
minikube start
kubectl apply -f .
```

## Connect from local machine

```bash
minikube ip
```

```bash
mongo --host <minikube-ip> --port 32017
```

```bash
mongo "mongodb://<username>:<password>@192.168.49.2:32017/admin"
```

```bash
show dbs
```

## Connect from a test pod

```bash
kubectl run mongo-client \
  --rm -i -t \
  --image=mongo \
  --namespace=mongotest \
  -- bash
```

Use mongo for older than v6.0, otherwise mongosh.
```bash
mongosh mongodb://<username>:<password>@mongodb:27017/admin
```

Or all at once:
```bash
kubectl run mongo-client \
  --rm -i -t \
  --image=mongo \
  --namespace=mongotest \
  -- \
  mongosh mongodb://<username>:<password>@mongodb:27017/admin
```
