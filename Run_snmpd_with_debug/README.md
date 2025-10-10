# Run snmpd with debug 

Small tips<br>

Debug all.
```
snmpd -f -Lo -DALL -Lf ./snmpd_dump_all.log
```

<br>If you are interested in the logs related to Agentx, run:
```
snmpd -f -Lo -Ddump,agentx -Lf ./snmpd_dump_agentx.log
```