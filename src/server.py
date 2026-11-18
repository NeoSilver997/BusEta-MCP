#!/usr/bin/env python3
"""
BusEta MCP Server
Hong Kong public transport ETA tools via Model Context Protocol.
Uses hk-bus-eta (supports KMB, CTB, GMB, MTR, NLB, etc.).
"""

import math
from typing import Optional
from mcp.server.fastmcp import FastMCP
from hk_bus_eta import HKEta

mcp = FastMCP("BusEta")
hketa = HKEta()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def _format_eta_list(etas, language="zh"):
    if not etas:
        return "No ETA data."
    lines = []
    for i, eta in enumerate(etas, 1):
        time = eta.get("eta", "N/A")
        remark = eta.get("remark", {})
        if isinstance(remark, dict):
            rem_text = remark.get(language, remark.get("zh", ""))
        else:
            rem_text = str(remark)
        co = eta.get("co", "")
        lines.append(f"{i}. {time}  {rem_text}  [{co}]")
    return "\n".join(lines)

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
        route_id: Full route ID from search_routes
        seq: Stop sequence index (0 = first stop)
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

    header = f"🚌 {route} → {dest} (stop seq {seq})\n"
    return header + _format_eta_list(etas, language)


@mcp.tool()
def get_stop_eta(stop_id: str, language: str = "zh") -> str:
    """
    Get ETA for ALL routes at a specific stop (by stop ID).

    Args:
        stop_id: Stop ID (from search_stops)
        language: "zh" or "en"
    """
    stop = hketa.stop_list.get(stop_id)
    if not stop:
        return f"Stop ID '{stop_id}' not found. Use search_stops first."

    name = stop.get("name", {}).get(language, stop.get("name", {}).get("zh", stop_id))
    lines = [f"Stop: {name} ({stop_id})\n"]

    # Find all routes that pass this stop and get their ETAs
    found = 0
    for route_id, info in hketa.route_list.items():
        stops = info.get("stops", {})
        stop_ids = []
        if isinstance(stops, dict):
            for ids in stops.values():
                if isinstance(ids, list):
                    stop_ids.extend(ids)
        elif isinstance(stops, list):
            stop_ids = stops

        if stop_id in stop_ids:
            try:
                seq = stop_ids.index(stop_id)
                etas = hketa.getEtas(route_id=route_id, seq=seq, language=language)
                if etas:
                    route = info.get("route", "?")
                    dest = info.get("dest", {}).get(language, "")
                    lines.append(f"\n🚌 {route} → {dest}")
                    lines.append(_format_eta_list(etas, language))
                    found += 1
            except Exception:
                continue

    if found == 0:
        lines.append("No live ETA found for this stop.")
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
    for i, sid in enumerate(stop_list):
        stop = hketa.stop_list.get(sid, {})
        name = stop.get("name", {}).get(language, stop.get("name", {}).get("zh", sid))
        lines.append(f"{i:3d}. {name}  ({sid})")

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
def nearby_stops(lat: float, lon: float, limit: int = 10, radius_m: int = 800) -> str:
    """
    Find nearest bus stops by latitude / longitude.

    Args:
        lat: Latitude (e.g. 22.3193)
        lon: Longitude (e.g. 114.1694)
        limit: Max stops to return
        radius_m: Search radius in metres (default 800)
    """
    candidates = []
    for stop_id, info in hketa.stop_list.items():
        loc = info.get("location", {})
        slat = loc.get("lat") or info.get("lat")
        slon = loc.get("lng") or info.get("long") or info.get("lng")
        if slat is None or slon is None:
            continue
        try:
            dist = _haversine(lat, lon, float(slat), float(slon))
        except Exception:
            continue
        if dist <= radius_m:
            name_zh = info.get("name", {}).get("zh", "")
            name_en = info.get("name", {}).get("en", "")
            candidates.append((dist, stop_id, name_zh, name_en))

    candidates.sort(key=lambda x: x[0])
    candidates = candidates[:limit]

    if not candidates:
        return f"No stops found within {radius_m}m."

    lines = [f"Nearest stops (within {radius_m}m):\n"]
    for dist, sid, zh, en in candidates:
        lines.append(f"• {zh} / {en}  ({sid})  — {int(dist)}m")
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


if __name__ == "__main__":
    mcp.run(transport="stdio")
