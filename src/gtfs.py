import csv
import os
from collections import defaultdict
from dataclasses import dataclass, field

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "gtfs")


@dataclass
class GtfsStop:
    stop_id: str
    stop_code: str
    stop_name: str
    stop_lat: float
    stop_lon: float


@dataclass
class GtfsRoute:
    route_id: str
    route_short_name: str
    route_long_name: str
    route_color: str
    route_text_color: str


@dataclass
class GtfsShapePoint:
    lat: float
    lon: float
    sequence: int


@dataclass
class GtfsFeed:
    stops_by_code: dict[str, GtfsStop] = field(default_factory=dict)
    stops_by_id: dict[str, GtfsStop] = field(default_factory=dict)
    routes_by_short_name: dict[str, GtfsRoute] = field(default_factory=dict)
    routes_by_id: dict[str, GtfsRoute] = field(default_factory=dict)
    shapes: dict[str, list[GtfsShapePoint]] = field(default_factory=dict)
    stop_route_names: dict[str, set[str]] = field(default_factory=dict)
    route_shapes: dict[str, dict[int, list[GtfsShapePoint]]] = field(default_factory=dict)


def _read_csv(path: str) -> list[dict[str, str]]:
    with open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _load_stops(feed_dir: str) -> tuple[dict[str, GtfsStop], dict[str, GtfsStop]]:
    by_code: dict[str, GtfsStop] = {}
    by_id: dict[str, GtfsStop] = {}
    for row in _read_csv(os.path.join(feed_dir, "stops.txt")):
        stop = GtfsStop(
            stop_id=row["stop_id"],
            stop_code=row.get("stop_code", ""),
            stop_name=row["stop_name"],
            stop_lat=float(row["stop_lat"]),
            stop_lon=float(row["stop_lon"]),
        )
        by_id[stop.stop_id] = stop
        if stop.stop_code:
            by_code[stop.stop_code] = stop
    return by_code, by_id


def _load_routes(feed_dir: str) -> tuple[dict[str, GtfsRoute], dict[str, GtfsRoute]]:
    by_short_name: dict[str, GtfsRoute] = {}
    by_id: dict[str, GtfsRoute] = {}
    for row in _read_csv(os.path.join(feed_dir, "routes.txt")):
        route = GtfsRoute(
            route_id=row["route_id"],
            route_short_name=row.get("route_short_name", ""),
            route_long_name=row.get("route_long_name", ""),
            route_color=row.get("route_color", ""),
            route_text_color=row.get("route_text_color", ""),
        )
        by_id[route.route_id] = route
        if route.route_short_name:
            by_short_name[route.route_short_name] = route
    return by_short_name, by_id


def _load_shapes(feed_dir: str) -> dict[str, list[GtfsShapePoint]]:
    shapes: dict[str, list[GtfsShapePoint]] = defaultdict(list)
    for row in _read_csv(os.path.join(feed_dir, "shapes.txt")):
        shapes[row["shape_id"]].append(
            GtfsShapePoint(
                lat=float(row["shape_pt_lat"]),
                lon=float(row["shape_pt_lon"]),
                sequence=int(row["shape_pt_sequence"]),
            )
        )
    for pts in shapes.values():
        pts.sort(key=lambda p: p.sequence)
    return dict(shapes)


def _build_associations(
    feed_dir: str,
    routes_by_id: dict[str, GtfsRoute],
    stops_by_id: dict[str, GtfsStop],
    shapes: dict[str, list[GtfsShapePoint]],
) -> tuple[dict[str, set[str]], dict[str, dict[int, list[GtfsShapePoint]]]]:
    """Build stop-route and route-shape associations from trips + stop_times."""
    trip_route: dict[str, str] = {}
    trip_direction: dict[str, int] = {}
    trip_shape: dict[str, str] = {}

    for row in _read_csv(os.path.join(feed_dir, "trips.txt")):
        tid = row["trip_id"]
        trip_route[tid] = row["route_id"]
        trip_direction[tid] = int(row.get("direction_id", "0"))
        trip_shape[tid] = row.get("shape_id", "")

    # stop_id -> set of route_short_name
    stop_routes: dict[str, set[str]] = defaultdict(set)
    seen_trip_stops: set[str] = set()

    for row in _read_csv(os.path.join(feed_dir, "stop_times.txt")):
        tid = row["trip_id"]
        sid = row["stop_id"]
        pair = f"{tid}:{sid}"
        if pair in seen_trip_stops:
            continue
        seen_trip_stops.add(pair)

        rid = trip_route.get(tid)
        if rid and rid in routes_by_id:
            route = routes_by_id[rid]
            code = stops_by_id[sid].stop_code if sid in stops_by_id else sid
            stop_routes[code].add(route.route_short_name)

    # route_short_name -> {direction: shape_points}
    route_shapes: dict[str, dict[int, list[GtfsShapePoint]]] = defaultdict(dict)
    best_shape_len: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))

    for tid, rid in trip_route.items():
        if rid not in routes_by_id:
            continue
        short = routes_by_id[rid].route_short_name
        d = trip_direction.get(tid, 0)
        shp = trip_shape.get(tid, "")
        if shp and shp in shapes:
            pts = shapes[shp]
            if len(pts) > best_shape_len[short][d]:
                best_shape_len[short][d] = len(pts)
                route_shapes[short][d] = pts

    return dict(stop_routes), dict(route_shapes)


def _load_feed(feed_dir: str) -> GtfsFeed:
    stops_by_code, stops_by_id = _load_stops(feed_dir)
    routes_by_short_name, routes_by_id = _load_routes(feed_dir)
    shapes = _load_shapes(feed_dir)
    stop_route_names, route_shapes = _build_associations(feed_dir, routes_by_id, stops_by_id, shapes)

    return GtfsFeed(
        stops_by_code=stops_by_code,
        stops_by_id=stops_by_id,
        routes_by_short_name=routes_by_short_name,
        routes_by_id=routes_by_id,
        shapes=shapes,
        stop_route_names=stop_route_names,
        route_shapes=route_shapes,
    )


bus_feed = _load_feed(os.path.join(_DATA_DIR, "bus"))
metro_feed = _load_feed(os.path.join(_DATA_DIR, "metro"))
