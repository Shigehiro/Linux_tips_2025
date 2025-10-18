# CoreDNS Remote logging with dnstap

## Reference

- [CoreDNS dnstap](https://coredns.io/plugins/dnstap/)
- [dnstap-receiver](https://pypi.org/project/dnstap-receiver/)

## Walkthrough logs

Run the containers
```
podman compose -f compose.yml up -d
```

<br>Four containers will be up and running as shown below.
```
$ podman compose ps
>>>> Executing external compose provider "/usr/libexec/docker/cli-plugins/docker-compose". Please see podman-compose(1) for how to disable this message. <<<<

NAME                                       IMAGE                                       COMMAND   SERVICE     CREATED          STATUS          PORTS
coredns_remotelogging_dnstap-coredns01-1   docker.io/coredns/coredns:latest            ""        coredns01   19 seconds ago   Up 18 seconds   53/tcp, 53/udp
coredns_remotelogging_dnstap-coredns02-1   docker.io/coredns/coredns:latest            ""        coredns02   19 seconds ago   Up 18 seconds   53/tcp, 53/udp
coredns_remotelogging_dnstap-dnstap-1      docker.io/dmachard/dnstap-receiver:latest   ""        dnstap      19 seconds ago   Up 18 seconds   6000/tcp, 8080/tcp
coredns_remotelogging_dnstap-netshoot-1    docker.io/nicolaka/netshoot:latest          "zsh"     netshoot    19 seconds ago   Up 18 seconds   
```

<br>Check the stdout logs of the dnstap-receiver container.
```
podman logs -f coredns_remotelogging_dnstap-dnstap-1 
```

<br>Send DNS queries from the netshoot container.
```
$ podman exec coredns_remotelogging_dnstap-netshoot-1 dig @172.16.10.10 www.google.com +short
142.251.222.36
$ podman exec coredns_remotelogging_dnstap-netshoot-1 dig @172.16.10.11 coredns.io +short
75.2.60.5
$ 
```

<br>You can find logs in the stdout of the dnstap-receiver container. Query logs are sent over TCP from the CoreDNS containers to the dnstap-receiver container.<br>
```
$ podman logs -f coredns_remotelogging_dnstap-dnstap-1 
{"identity": "8961d7ead516", "qname": "www.google.com.", "rrtype": "A", "query-ip": "172.16.10.2", "query-port": 54595, "response-ip": "-", "response-port": "-", "latency": "-", "message": "CLIENT_QUERY", "family": "INET", "protocol": "UDP", "length": 55, "timestamp": 1760794077.8110669, "type": "query", "rcode": "NOERROR", "id": 34505, "datetime": "2025-10-18T13:27:57.811067+00:00"}
{"identity": "8961d7ead516", "qname": "www.google.com.", "rrtype": "A", "query-ip": "172.16.10.2", "query-port": 54595, "response-ip": "8.8.8.8", "response-port": 53, "latency": "-", "message": "FORWARDER_QUERY", "family": "INET", "protocol": "UDP", "length": 55, "timestamp": 1760794077.8111024, "type": "query", "rcode": "NOERROR", "id": 34505, "datetime": "2025-10-18T13:27:57.811102+00:00"}
{"identity": "8961d7ead516", "qname": "www.google.com.", "rrtype": "A", "query-ip": "172.16.10.2", "query-port": 54595, "response-ip": "8.8.8.8", "response-port": 53, "latency": 0.014, "message": "FORWARDER_RESPONSE", "family": "INET", "protocol": "UDP", "length": 73, "timestamp": 1760794077.8254056, "type": "response", "rcode": "NOERROR", "id": 34505, "datetime": "2025-10-18T13:27:57.825406+00:00"}
{"identity": "8961d7ead516", "qname": "www.google.com.", "rrtype": "A", "query-ip": "172.16.10.2", "query-port": 54595, "response-ip": "-", "response-port": "-", "latency": 0.014, "message": "CLIENT_RESPONSE", "family": "INET", "protocol": "UDP", "length": 85, "timestamp": 1760794077.8255055, "type": "response", "rcode": "NOERROR", "id": 34505, "datetime": "2025-10-18T13:27:57.825505+00:00"}
{"identity": "831012f73b93", "qname": "coredns.io.", "rrtype": "A", "query-ip": "172.16.10.2", "query-port": 57064, "response-ip": "-", "response-port": "-", "latency": "-", "message": "CLIENT_QUERY", "family": "INET", "protocol": "UDP", "length": 51, "timestamp": 1760794095.6029987, "type": "query", "rcode": "NOERROR", "id": 59951, "datetime": "2025-10-18T13:28:15.602999+00:00"}
{"identity": "831012f73b93", "qname": "coredns.io.", "rrtype": "A", "query-ip": "172.16.10.2", "query-port": 57064, "response-ip": "8.8.8.8", "response-port": 53, "latency": "-", "message": "FORWARDER_QUERY", "family": "INET", "protocol": "UDP", "length": 51, "timestamp": 1760794095.6030598, "type": "query", "rcode": "NOERROR", "id": 59951, "datetime": "2025-10-18T13:28:15.603060+00:00"}
{"identity": "831012f73b93", "qname": "coredns.io.", "rrtype": "A", "query-ip": "172.16.10.2", "query-port": 57064, "response-ip": "8.8.8.8", "response-port": 53, "latency": 0.241, "message": "FORWARDER_RESPONSE", "family": "INET", "protocol": "UDP", "length": 65, "timestamp": 1760794095.8445156, "type": "response", "rcode": "NOERROR", "id": 59951, "datetime": "2025-10-18T13:28:15.844516+00:00"}
{"identity": "831012f73b93", "qname": "coredns.io.", "rrtype": "A", "query-ip": "172.16.10.2", "query-port": 57064, "response-ip": "-", "response-port": "-", "latency": 0.242, "message": "CLIENT_RESPONSE", "family": "INET", "protocol": "UDP", "length": 77, "timestamp": 1760794095.844662, "type": "response", "rcode": "NOERROR", "id": 59951, "datetime": "2025-10-18T13:28:15.844662+00:00"}
```

<br>You can also view the DNS query logs from the file.
```
$ podman exec coredns_remotelogging_dnstap-dnstap-1 tail -1 /home/dnstap/logs/dnstap.json
{"identity": "831012f73b93", "qname": "coredns.io.", "rrtype": "A", "query-ip": "172.16.10.2", "query-port": 57064, "response-ip": "-", "response-port": "-", "latency": 0.242, "message": "CLIENT_RESPONSE", "family": "INET", "protocol": "UDP", "length": 77, "timestamp": 1760794095.844662, "type": "response", "rcode": "NOERROR", "id": 59951, "datetime": "2025-10-18T13:28:15.844662+00:00"}
```
