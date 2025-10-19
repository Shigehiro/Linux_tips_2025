# CoreDNS DNSTap and Kafka integration

## Description

Here is how to aggregate and centralize DNS query logs with dnstap and Kafka.

## Network Topology

```
coredns01 -----
               | ------------ dnstap-receiver ---------------- kafka
coredns02 -----
           dnstap over TCP                     produce logs
```

## How to test

Build the containers.
```
docker compose -f compose.yml build
```

<br>Run the containers.
```
docker compose -f compose.yml up -d
```

<br>Five containers will be up and running.
```
$ docker compose -f compose.yml ps
NAME                               IMAGE                                COMMAND                  SERVICE     CREATED         STATUS         PORTS
coredns_dnstap_kafka-coredns01-1   docker.io/coredns/coredns:latest     "/coredns"               coredns01   5 seconds ago   Up 4 seconds   53/tcp, 53/udp
coredns_dnstap_kafka-coredns02-1   docker.io/coredns/coredns:latest     "/coredns"               coredns02   5 seconds ago   Up 4 seconds   53/tcp, 53/udp
coredns_dnstap_kafka-dnstap-1      coredns_dnstap_kafka-dnstap          "dnstap_receiver -c …"   dnstap      4 seconds ago   Up 3 seconds   
coredns_dnstap_kafka-kafka-1       docker.io/apache/kafka:4.0.1         "/__cacert_entrypoin…"   kafka       5 seconds ago   Up 4 seconds   9092/tcp
coredns_dnstap_kafka-netshoot-1    docker.io/nicolaka/netshoot:latest   "zsh"                    netshoot    5 seconds ago   Up 4 seconds  
```

<br>Create the topic on the Kafka container.
```
docker exec -it -w /opt/kafka/bin coredns_dnstap_kafka-kafka-1 sh
```

<br>In the kafka container:
```
/opt/kafka/bin $ ./kafka-topics.sh --bootstrap-server localhost:9092 --create --topic dnstap-topic
```

Two CoreDNS containers are running. Send DNS queries to both.
```
docker exec coredns_dnstap_kafka-netshoot-1 dig @172.16.10.10 www.google.com +short
```

```
docker exec coredns_dnstap_kafka-netshoot-1 dig @172.16.10.11 www.cisco.com +short
```

<br>Consume the topic.
```
$  docker exec -it -w /opt/kafka/bin coredns_dnstap_kafka-kafka-1 sh
/opt/kafka/bin $ ./kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic dnstap-topic --from-beginning
{"identity": "e0a92c8facdd", "qname": "www.google.com.", "rrtype": "A", "query-ip": "172.16.10.2", "query-port": 60241, "response-ip": "8.8.8.8", "response-port": 53, "latency": 0.012, "message": "FORWARDER_RESPONSE", "family": "INET", "protocol": "UDP", "length": 73, "timestamp": 1760858167.8799415, "type": "response", "rcode": "NOERROR", "id": 60733, "datetime": "2025-10-19T07:16:07.879941+00:00"}
{"identity": "f0f96fd45773", "qname": "www.cisco.com.", "rrtype": "A", "query-ip": "172.16.10.2", "query-port": 42978, "response-ip": "-", "response-port": "-", "latency": "-", "message": "CLIENT_QUERY", "family": "INET", "protocol": "UDP", "length": 54, "timestamp": 1760858180.887117, "type": "query", "rcode": "NOERROR", "id": 24617, "datetime": "2025-10-19T07:16:20.887117+00:00"}
{"identity": "f0f96fd45773", "qname": "www.cisco.com.", "rrtype": "A", "query-ip": "172.16.10.2", "query-port": 42978, "response-ip": "8.8.8.8", "response-port": 53, "latency": "-", "message": "FORWARDER_QUERY", "family": "INET", "protocol": "UDP", "length": 54, "timestamp": 1760858180.8872223, "type": "query", "rcode": "NOERROR", "id": 24617, "datetime": "2025-10-19T07:16:20.887222+00:00"}
{"identity": "f0f96fd45773", "qname": "www.cisco.com.", "rrtype": "A", "query-ip": "172.16.10.2", "query-port": 42978, "response-ip": "8.8.8.8", "response-port": 53, "latency": 0.018, "message": "FORWARDER_RESPONSE", "family": "INET", "protocol": "UDP", "length": 379, "timestamp": 1760858180.904773, "type": "response", "rcode": "NOERROR", "id": 24617, "datetime": "2025-10-19T07:16:20.904773+00:00"}
{"identity": "f0f96fd45773", "qname": "www.cisco.com.", "rrtype": "A", "query-ip": "172.16.10.2", "query-port": 42978, "response-ip": "-", "response-port": "-", "latency": 0.018, "message": "CLIENT_RESPONSE", "family": "INET", "protocol": "UDP", "length": 391, "timestamp": 1760858180.9050665, "type": "response", "rcode": "NOERROR", "id": 24617, "datetime": "2025-10-19T07:16:20.905066+00:00"}
{"identity": "e0a92c8facdd", "qname": "www.google.com.", "rrtype": "A", "query-ip": "172.16.10.2", "query-port": 60241, "response-ip": "-", "response-port": "-", "latency": "-", "message": "CLIENT_QUERY", "family": "INET", "protocol": "UDP", "length": 55, "timestamp": 1760858167.8675802, "type": "query", "rcode": "NOERROR", "id": 60733, "datetime": "2025-10-19T07:16:07.867580+00:00"}
{"identity": "e0a92c8facdd", "qname": "www.google.com.", "rrtype": "A", "query-ip": "172.16.10.2", "query-port": 60241, "response-ip": "8.8.8.8", "response-port": 53, "latency": "-", "message": "FORWARDER_QUERY", "family": "INET", "protocol": "UDP", "length": 55, "timestamp": 1760858167.8676906, "type": "query", "rcode": "NOERROR", "id": 60733, "datetime": "2025-10-19T07:16:07.867691+00:00"}
{"identity": "e0a92c8facdd", "qname": "www.google.com.", "rrtype": "A", "query-ip": "172.16.10.2", "query-port": 60241, "response-ip": "-", "response-port": "-", "latency": 0.012, "message": "CLIENT_RESPONSE", "family": "INET", "protocol": "UDP", "length": 85, "timestamp": 1760858167.880077, "type": "response", "rcode": "NOERROR", "id": 60733, "datetime": "2025-10-19T07:16:07.880077+00:00"}
```