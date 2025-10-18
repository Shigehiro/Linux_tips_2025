# Run knot resolver on Podman

## Pull the image
```
podman pull docker.io/cznic/knot-resolver:6
```

## Prepare the config file

knot-resolver-config.yaml
```yaml
# Number of worker processes to handle queries
workers: 2

# Network interface configuration
network:
  listen:
    # Listen for unencrypted DNS (UDP/TCP) on localhost port 53
    - interface: 0.0.0.0@53

# Management API configuration (for kresctl utility)
management:
  # Unix socket for local management
  unix-socket: /run/knot-resolver/kres-api.sock
```

## Run the container
```
podman container run --rm -d --network podman1 --ip 10.90.0.10 -v ./knot-resolver-config.yaml:/etc/knot-resolver/config.yaml:ro docker.io/cznic/knot-resolver:6 
```

## Confirm the container is running
```
$ podman container run --rm --network podman1 docker.io/nicolaka/netshoot:latest dig @10.90.0.10 www.google.com +short
142.251.222.36
```
