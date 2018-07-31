# mackerel-client
Mackerel system client. For use with a [Mackerel server](wkumakerspace/mackerel-server) instance.

Requires Python 3.6.

## Usage
```python
from MackerelClient import MackerelClient

# type is one of 'kiosk', 'tool', 'admin'
client = MackerelClient(name, type)

self.ip = SERVER_IP
self.port = SERVER_PORT

self.connect()

self.run_command(cmd, *args)
```
