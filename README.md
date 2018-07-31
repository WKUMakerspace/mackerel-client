# mackerel-client
Mackerel system client. For use with a [Mackerel server](https://github.com/wkumakerspace/mackerel-server) instance.

Requires Python 3.6.

## Usage
```python
from MackerelClient import MackerelClient

# type is one of 'kiosk', 'tool', 'admin'
client = MackerelClient(name, type)

client.ip = SERVER_IP
client.port = SERVER_PORT

client.connect()

if client.socket:
  client.run_command(cmd, *args)
```
