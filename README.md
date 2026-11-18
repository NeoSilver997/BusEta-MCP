# BusEta MCP Server

Hong Kong Bus ETA Model Context Protocol (MCP) server.

Connects AI assistants (Claude Desktop, Cursor, XiaoZhi, etc.) to real-time Hong Kong bus arrival times.

Supports: KMB, CTB, GMB, MTR, Light Rail, NLB and more via `hk-bus-eta`.

## Features

- Search routes by number or keyword (Chinese / English)
- Get real-time ETA for a stop on a route
- Get ETA for **all routes at a stop** (by stop ID)
- List stops for a route
- Search stops by name
- Find **nearby stops** by lat/lon
- Bilingual output

## Setup

```bash
pip install -r requirements.txt
python src/server.py
```

## Claude Desktop / MCP Client Config

```json
{
  "mcpServers": {
    "buseta": {
      "command": "python",
      "args": ["/absolute/path/to/BusEta-MCP/src/server.py"]
    }
  }
}
```

## Tools

| Tool | Description |
|------|-------------|
| `search_routes` | Search bus routes by keyword |
| `get_route_eta` | Get ETA for a specific route + stop sequence |
| `get_stop_eta` | Get ETA for **all routes** at a stop ID |
| `get_route_stops` | List all stops of a route |
| `search_stops` | Search stops by name |
| `nearby_stops` | Find nearest stops by latitude / longitude |
| `get_server_info` | Server status |

## Data Sources

- `hk-bus-eta` (aggregates data.gov.hk, data.etabus.gov.hk, etc.)
- Official open data from Transport Department

## License

MIT
