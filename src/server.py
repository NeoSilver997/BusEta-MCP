#!/usr/bin/env python3
"""
BusEta MCP Server
Hong Kong public transport ETA tools via Model Context Protocol.
"""

from typing import Optional
from mcp.server.fastmcp import FastMCP
from hk_bus_eta import HKEta

# Initialize
mcp = FastMCP("BusEta")
hketa = HKEta()

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def search_routes(keyword: str, limit: int = 20) -> str:
    """
    Search Hong Kong bus routes by route number or destination keyword.

    Args:
        keyword: Route number (e.g. "1", "968", "A21") or destination text
        limit: Max results to return (default 20)
    """
    keyword = keyword.strip().upper()
    results = []

    for route_id, info in hketa.route_list.items():
        route = info.get("route", "")
        orig_zh = info.get("orig", {}).get("zh", "")
        dest_zh = info.get("dest", {}).get("zh", "")
        orig_en = info.get("orig", {}).get("en", "")
        dest_en = info.get("dest", {}).get("en", "")
        companies = ", ".join(info.get("co", []))

        searchable = f"{route} {orig_zh} {dest_zh} {orig_en} {dest_en}".upper()

        if keyword in searchable or keyword in route.upper():
            results.append({
                "route_id": route_id,
                "route": route,
                "from": f"{orig_zh} / {orig_en}",
                "to": f"{dest_zh} / {dest_en}",
                "companies": companies,
            })
            if len(results) >= limit:
                break

    if not results:
        return f"No routes found for '{keyword}'."

    lines = [f"Found {len(results)} route(s) for '{keyword}':\n"]
    for r in results:
        lines.append(
            f"• {r['route']}  ({r['route_id']})\n"
            f"  {r['from']} → {r['to']}\n"
            f"  Operators: {r['companies']}\n"
        )
    return "\n".join(lines)


@mcp.tool()
def get_route_eta(route_id: str, seq: int = 0, language: str = "zh") -> str:
    """
    Get real-time ETA for a specific stop on a route.

    Args:
        route_id: Full route ID from search_routes (e.g. "1+1+CHUK YUEN ESTATE+STAR FERRY")
        seq: Stop sequence index (0 = first stop). Use get_route_stops to find the right seq.
        language: "zh" or "en"
    """
    if route_id not in hketa.route_list:
        return f"Route ID '{route_id}' not found. Use search_routes first."

    try:
        etas = hketa.getEtas(route_id=route_id, seq=seq, language=language)
    except Exception as e:
        return f"Error fetching ETA: {e}"

    if not etas:
        return f"No ETA data available for {route_id} at seq={seq}."

    route_info = hketa.route_list[route_id]
    route = route_info.get("route", "?")
    dest = route_info.get("dest", {}).get("zh" if language == "zh" else "en", "")

    lines = [f"🚌 {route} → {dest} (stop seq {seq})\n"]
    for i, eta in enumerate(etas, 1):
        time = eta.get("eta", "N/A")
        remark = eta.get("remark", {})
        rem_text = remark.get(language, remark.get("zh", "")) if isinstance(remark, dict) else str(remark)
        co = eta.get("co", "")
        lines.append(f"{i}. {time}  {rem_text}  [{co}]")

    return "\n".join(lines)


@mcp.tool()
def get_route_stops(route_id: str, language: str = "zh") -> str:
    """
    List all stops for a route with their sequence numbers.

    Args:
        route_id: Full route ID
        language: "zh" or "en"
    """
    if route_id not in hketa.route_list:
        return f"Route ID '{route_id}' not found."

    info = hketa.route_list[route_id]
    stops = info.get("stops", {})
    # stops is usually { "1": [stop_ids...], "2": [...] } or similar
    # Normalize
    stop_list = []
    if isinstance(stops, dict):
        for bound, ids in stops.items():
            if isinstance(ids, list):
                stop_list.extend(ids)
    elif isinstance(stops, list):
        stop_list = stops

    if not stop_list:
        return "No stop information available for this route."

    lines = [f"Stops for {info.get('route', route_id)}:\n"]
    for i, stop_id in enumerate(stop_list):
        stop = hketa.stop_list.get(stop_id, {})
        name = stop.get("name", {}).get(language, stop.get("name", {}).get("zh", stop_id))
        lines.append(f"{i:3d}. {name}  ({stop_id})")

    lines.append("\nUse the sequence number (left) with get_route_eta.")
    return "\n".join(lines)


@mcp.tool()
def search_stops(keyword: str, limit: int = 15) -> str:
    """
    Search bus stops by Chinese or English name.

    Args:
        keyword: Stop name fragment
        limit: Max results
    """
    keyword = keyword.strip().lower()
    results = []

    for stop_id, info in hketa.stop_list.items():
        name_zh = info.get("name", {}).get("zh", "").lower()
        name_en = info.get("name", {}).get("en", "").lower()
        if keyword in name_zh or keyword in name_en:
            results.append({
                "stop_id": stop_id,
                "name_zh": info.get("name", {}).get("zh", ""),
                "name_en": info.get("name", {}).get("en", ""),
            })
            if len(results) >= limit:
                break

    if not results:
        return f"No stops found matching '{keyword}'."

    lines = [f"Stops matching '{keyword}':\n"]
    for r in results:
        lines.append(f"• {r['name_zh']} / {r['name_en']}  ({r['stop_id']})")
    return "\n".join(lines)


@mcp.tool()
def get_server_info() -> str:
    """Return basic server and data status."""
    route_count = len(hketa.route_list)
    stop_count = len(hketa.stop_list)
    return (
        f"BusEta MCP Server\n"
        f"Routes loaded: {route_count}\n"
        f"Stops loaded: {stop_count}\n"
        f"Data source: hk-bus-eta (data.gov.hk + official ETA APIs)\n"
        f"Status: Ready"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
