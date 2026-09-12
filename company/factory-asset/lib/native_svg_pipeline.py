from __future__ import annotations

import hashlib
import io
import json
import math
import re
import xml.etree.ElementTree as ET
from typing import Any, Iterable

from PIL import Image, ImageDraw


SVG_NS = "http://www.w3.org/2000/svg"
ALLOWED_TAGS = {
    "svg",
    "g",
    "path",
    "rect",
    "circle",
    "ellipse",
    "line",
    "polyline",
    "polygon",
}
FORBIDDEN_TAGS = {
    "script",
    "image",
    "text",
    "foreignObject",
    "use",
    "style",
    "defs",
    "symbol",
    "iframe",
    "audio",
    "video",
}
PATH_COMMANDS = set("MLHVZCSQTAmlhvzcsqta")
PATH_PARAMETER_COUNTS = {
    "M": 2,
    "L": 2,
    "H": 1,
    "V": 1,
    "C": 6,
    "S": 4,
    "Q": 4,
    "T": 2,
    "A": 7,
}
NUMBER_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")
URLISH = re.compile(r"url\s*\(|(?:https?|file|data):", re.IGNORECASE)
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.:-]*$")
CURVE_STEPS = 16
ARC_STEPS_PER_QUARTER = 8
MAX_RENDER_SIZE = 4096
MAX_RENDER_PIXELS = 16_777_216
MAX_XML_NODES = 4096
MAX_GROUP_DEPTH = 64
IDENTITY_MATRIX = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

STYLE_ATTRS = {
    "fill",
    "stroke",
    "stroke-width",
    "fill-opacity",
    "stroke-opacity",
    "opacity",
    "fill-rule",
    "stroke-linecap",
    "stroke-linejoin",
    "stroke-miterlimit",
}
COMMON_ATTRS = STYLE_ATTRS | {"id", "class", "transform"}
ROOT_ATTRS = COMMON_ATTRS | {"viewbox", "width", "height", "version"}
GEOMETRY_ATTRS = {
    "path": {"d"},
    "rect": {"x", "y", "width", "height", "rx", "ry"},
    "circle": {"cx", "cy", "r"},
    "ellipse": {"cx", "cy", "rx", "ry"},
    "line": {"x1", "y1", "x2", "y2"},
    "polyline": {"points"},
    "polygon": {"points"},
}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
SHORT_HEX = re.compile(r"^#[0-9a-fA-F]{3}$")
RGB = re.compile(r"^rgb\(\s*([0-9]+)\s*,\s*([0-9]+)\s*,\s*([0-9]+)\s*\)$", re.IGNORECASE)
NAMED_COLORS = {
    "black": "#000000",
    "blue": "#0000ff",
    "gray": "#808080",
    "green": "#008000",
    "grey": "#808080",
    "orange": "#ffa500",
    "purple": "#800080",
    "red": "#ff0000",
    "white": "#ffffff",
    "yellow": "#ffff00",
}


class NativeSvgPipelineError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_value(value: Any) -> str:
    return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _namespace(tag: str) -> str | None:
    return tag[1:].split("}", 1)[0] if tag.startswith("{") and "}" in tag else None


def _format_number(value: float) -> str:
    if not math.isfinite(value):
        raise NativeSvgPipelineError("GEOMETRY_NONFINITE", str(value))
    if abs(value) < 1e-12:
        value = 0.0
    return format(value, ".12g")


def _format_transform(matrix: tuple[float, float, float, float, float, float]) -> str | None:
    if all(abs(a - b) < 1e-12 for a, b in zip(matrix, IDENTITY_MATRIX)):
        return None
    return "matrix(" + " ".join(_format_number(x) for x in matrix) + ")"


def _color(value: str | None, *, default: str) -> str:
    value = (value or default).strip().casefold()
    if value == "none":
        return value
    if value in NAMED_COLORS:
        return NAMED_COLORS[value]
    if SHORT_HEX.fullmatch(value):
        return "#" + "".join(ch * 2 for ch in value[1:])
    if HEX.fullmatch(value):
        return value.lower()
    match = RGB.fullmatch(value)
    if match and all(int(part) <= 255 for part in match.groups()):
        return "#" + "".join(f"{int(part):02x}" for part in match.groups())
    raise NativeSvgPipelineError("COLOR_UNSAFE", value)


def _rgb(value: str) -> tuple[int, int, int]:
    if value == "none":
        return 0, 0, 0
    return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))


def _finite_float(value: str, *, code: str, context: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise NativeSvgPipelineError(code, context) from exc
    if not math.isfinite(parsed):
        raise NativeSvgPipelineError(code, context)
    return parsed


def _parse_number_tokens(value: str, *, commands: bool = False) -> list[float | str]:
    tokens: list[float | str] = []
    position = 0
    while position < len(value):
        if value[position].isspace() or value[position] == ",":
            position += 1
            continue
        if commands and value[position] in PATH_COMMANDS:
            tokens.append(value[position])
            position += 1
            continue
        match = NUMBER_RE.match(value, position)
        if not match:
            code = "PATH_COMMAND_UNSUPPORTED" if commands else "POINTS_SYNTAX_INVALID"
            raise NativeSvgPipelineError(code, value[max(0, position - 20) : position + 40])
        number = _finite_float(match.group(0), code="PATH_NONFINITE", context=match.group(0))
        tokens.append(number)
        position = match.end()
    return tokens


def _parse_path_commands(d: str) -> list[tuple[Any, ...]]:
    if not d:
        raise NativeSvgPipelineError("PATH_EMPTY", d)
    tokens = _parse_number_tokens(d, commands=True)
    commands: list[tuple[Any, ...]] = []
    index = 0
    command: str | None = None
    current = (0.0, 0.0)
    start: tuple[float, float] | None = None
    previous_op: str | None = None
    previous_cubic_control: tuple[float, float] | None = None
    previous_quadratic_control: tuple[float, float] | None = None

    while index < len(tokens):
        if isinstance(tokens[index], str):
            command = tokens[index]
            index += 1
            if command.upper() == "Z":
                if start is None:
                    raise NativeSvgPipelineError("PATH_SYNTAX_INVALID", d[:200])
                commands.append(("Z",))
                current = start
                previous_op = "Z"
                previous_cubic_control = None
                previous_quadratic_control = None
                command = None
                continue
        if command is None:
            raise NativeSvgPipelineError("PATH_SYNTAX_INVALID", d[:200])
        op = command.upper()
        count = PATH_PARAMETER_COUNTS.get(op)
        if count is None:
            raise NativeSvgPipelineError("PATH_COMMAND_UNSUPPORTED", command)
        if index + count > len(tokens) or any(isinstance(x, str) for x in tokens[index : index + count]):
            raise NativeSvgPipelineError("PATH_SYNTAX_INVALID", d[:200])
        values = [float(x) for x in tokens[index : index + count]]
        index += count
        relative = command.islower()

        if op == "M":
            x, y = values
            if relative:
                x += current[0]
                y += current[1]
            current = (x, y)
            start = current
            commands.append(("M", x, y))
            previous_op = "M"
            previous_cubic_control = None
            previous_quadratic_control = None
            command = "l" if relative else "L"
        elif op == "L":
            x, y = values
            if relative:
                x += current[0]
                y += current[1]
            current = (x, y)
            commands.append(("L", x, y))
            previous_op = "L"
            previous_cubic_control = None
            previous_quadratic_control = None
        elif op == "H":
            x = values[0] + current[0] if relative else values[0]
            current = (x, current[1])
            commands.append(("L", *current))
            previous_op = "L"
            previous_cubic_control = None
            previous_quadratic_control = None
        elif op == "V":
            y = values[0] + current[1] if relative else values[0]
            current = (current[0], y)
            commands.append(("L", *current))
            previous_op = "L"
            previous_cubic_control = None
            previous_quadratic_control = None
        elif op == "C":
            x1, y1, x2, y2, x, y = values
            if relative:
                x1, y1 = x1 + current[0], y1 + current[1]
                x2, y2, x = x2 + current[0], y2 + current[1], x + current[0]
                y = y + current[1]
            commands.append(("C", x1, y1, x2, y2, x, y))
            current = (x, y)
            previous_op = "C"
            previous_cubic_control = (x2, y2)
            previous_quadratic_control = None
        elif op == "S":
            x2, y2, x, y = values
            if relative:
                x2, y2, x, y = x2 + current[0], y2 + current[1], x + current[0], y + current[1]
            if previous_op in {"C", "S"} and previous_cubic_control is not None:
                x1 = 2 * current[0] - previous_cubic_control[0]
                y1 = 2 * current[1] - previous_cubic_control[1]
            else:
                x1, y1 = current
            commands.append(("C", x1, y1, x2, y2, x, y))
            current = (x, y)
            previous_op = "S"
            previous_cubic_control = (x2, y2)
            previous_quadratic_control = None
        elif op == "Q":
            x1, y1, x, y = values
            if relative:
                x1, y1, x, y = x1 + current[0], y1 + current[1], x + current[0], y + current[1]
            commands.append(("Q", x1, y1, x, y))
            current = (x, y)
            previous_op = "Q"
            previous_cubic_control = None
            previous_quadratic_control = (x1, y1)
        elif op == "T":
            x, y = values
            if relative:
                x, y = x + current[0], y + current[1]
            if previous_op in {"Q", "T"} and previous_quadratic_control is not None:
                x1 = 2 * current[0] - previous_quadratic_control[0]
                y1 = 2 * current[1] - previous_quadratic_control[1]
            else:
                x1, y1 = current
            commands.append(("Q", x1, y1, x, y))
            current = (x, y)
            previous_op = "T"
            previous_cubic_control = None
            previous_quadratic_control = (x1, y1)
        elif op == "A":
            rx, ry, rotation, large, sweep, x, y = values
            if relative:
                x, y = x + current[0], y + current[1]
            if large not in {0.0, 1.0} or sweep not in {0.0, 1.0}:
                raise NativeSvgPipelineError("PATH_FLAG_INVALID", d[:200])
            commands.append(("A", abs(rx), abs(ry), rotation, int(large), int(sweep), x, y))
            current = (x, y)
            previous_op = "A"
            previous_cubic_control = None
            previous_quadratic_control = None
        else:
            raise NativeSvgPipelineError("PATH_COMMAND_UNSUPPORTED", command)

    if not commands or not any(command[0] in {"L", "C", "Q", "A"} for command in commands):
        raise NativeSvgPipelineError("PATH_EMPTY", d[:200])
    return commands


def _parse_points(value: str) -> list[tuple[float, float]]:
    tokens = _parse_number_tokens(value)
    if len(tokens) < 4 or len(tokens) % 2 or any(isinstance(token, str) for token in tokens):
        raise NativeSvgPipelineError("POINTS_SYNTAX_INVALID", value[:200])
    return [(float(tokens[index]), float(tokens[index + 1])) for index in range(0, len(tokens), 2)]


def _matrix_multiply(
    left: tuple[float, float, float, float, float, float],
    right: tuple[float, float, float, float, float, float],
) -> tuple[float, float, float, float, float, float]:
    a, b, c, d, e, f = left
    g, h, i, j, k, l = right
    return (a * g + c * h, b * g + d * h, a * i + c * j, b * i + d * j, a * k + c * l + e, b * k + d * l + f)


def _apply_matrix(point: tuple[float, float], matrix: tuple[float, float, float, float, float, float]) -> tuple[float, float]:
    a, b, c, d, e, f = matrix
    x, y = point
    return a * x + c * y + e, b * x + d * y + f


def _parse_transform(value: str | None) -> tuple[float, float, float, float, float, float]:
    if not value:
        return IDENTITY_MATRIX
    position = 0
    result = IDENTITY_MATRIX
    while position < len(value):
        while position < len(value) and (value[position].isspace() or value[position] == ","):
            position += 1
        match = re.match(r"(matrix|translate|scale|rotate)\s*\(", value[position:], re.IGNORECASE)
        if not match:
            raise NativeSvgPipelineError("TRANSFORM_UNSUPPORTED", value[:200])
        name = match.group(1).casefold()
        position += match.end()
        close = value.find(")", position)
        if close < 0:
            raise NativeSvgPipelineError("TRANSFORM_INVALID", value[:200])
        raw_args = value[position:close]
        args = _parse_number_tokens(raw_args)
        if any(isinstance(arg, str) for arg in args):
            raise NativeSvgPipelineError("TRANSFORM_INVALID", value[:200])
        numbers = [float(arg) for arg in args]
        if name == "matrix" and len(numbers) == 6:
            matrix = tuple(numbers)  # type: ignore[assignment]
        elif name == "translate" and len(numbers) in {1, 2}:
            matrix = (1.0, 0.0, 0.0, 1.0, numbers[0], numbers[1] if len(numbers) == 2 else 0.0)
        elif name == "scale" and len(numbers) in {1, 2}:
            matrix = (numbers[0], 0.0, 0.0, numbers[1] if len(numbers) == 2 else numbers[0], 0.0, 0.0)
        elif name == "rotate" and len(numbers) in {1, 3}:
            angle = math.radians(numbers[0])
            cos_angle, sin_angle = math.cos(angle), math.sin(angle)
            rotation = (cos_angle, sin_angle, -sin_angle, cos_angle, 0.0, 0.0)
            if len(numbers) == 3:
                cx, cy = numbers[1:]
                matrix = _matrix_multiply(
                    _matrix_multiply((1.0, 0.0, 0.0, 1.0, cx, cy), rotation),
                    (1.0, 0.0, 0.0, 1.0, -cx, -cy),
                )
            else:
                matrix = rotation
        else:
            raise NativeSvgPipelineError("TRANSFORM_INVALID", value[:200])
        if not all(math.isfinite(number) for number in matrix):
            raise NativeSvgPipelineError("TRANSFORM_INVALID", value[:200])
        result = _matrix_multiply(result, matrix)
        position = close + 1
    return result


def _arc_points(
    start: tuple[float, float],
    rx: float,
    ry: float,
    rotation: float,
    large: int,
    sweep: int,
    end: tuple[float, float],
) -> list[tuple[float, float]]:
    if start == end or rx == 0 or ry == 0:
        return [end]
    rx, ry = abs(rx), abs(ry)
    angle = math.radians(rotation % 360.0)
    cos_angle, sin_angle = math.cos(angle), math.sin(angle)
    dx = (start[0] - end[0]) / 2.0
    dy = (start[1] - end[1]) / 2.0
    x_prime = cos_angle * dx + sin_angle * dy
    y_prime = -sin_angle * dx + cos_angle * dy
    radii_ratio = (x_prime * x_prime) / (rx * rx) + (y_prime * y_prime) / (ry * ry)
    if radii_ratio > 1:
        factor = math.sqrt(radii_ratio)
        rx *= factor
        ry *= factor
    numerator = max(0.0, (rx * rx * ry * ry) - (rx * rx * y_prime * y_prime) - (ry * ry * x_prime * x_prime))
    denominator = rx * rx * y_prime * y_prime + ry * ry * x_prime * x_prime
    factor = 0.0 if denominator == 0 else math.sqrt(numerator / denominator)
    if bool(large) == bool(sweep):
        factor = -factor
    cx_prime = factor * (rx * y_prime / ry)
    cy_prime = factor * (-ry * x_prime / rx)
    cx = cos_angle * cx_prime - sin_angle * cy_prime + (start[0] + end[0]) / 2.0
    cy = sin_angle * cx_prime + cos_angle * cy_prime + (start[1] + end[1]) / 2.0

    def unit_angle(ux: float, uy: float, vx: float, vy: float) -> float:
        return math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)

    ux, uy = (x_prime - cx_prime) / rx, (y_prime - cy_prime) / ry
    vx, vy = (-x_prime - cx_prime) / rx, (-y_prime - cy_prime) / ry
    start_angle = math.atan2(uy, ux)
    delta = unit_angle(ux, uy, vx, vy)
    if not sweep and delta > 0:
        delta -= 2 * math.pi
    elif sweep and delta < 0:
        delta += 2 * math.pi
    steps = max(1, min(128, int(math.ceil(abs(delta) / (math.pi / ARC_STEPS_PER_QUARTER)))))
    points = []
    for step in range(1, steps + 1):
        theta = start_angle + delta * step / steps
        points.append(
            (
                cx + rx * (cos_angle * math.cos(theta) - sin_angle * math.sin(theta)),
                cy + ry * (sin_angle * math.cos(theta) + cos_angle * math.sin(theta)),
            )
        )
    points[-1] = end
    return points


def _curve_points(start: tuple[float, float], command: tuple[Any, ...]) -> list[tuple[float, float]]:
    op = command[0]
    if op == "C":
        _, p1x, p1y, p2x, p2y, ex, ey = command
        p1, p2, end = (p1x, p1y), (p2x, p2y), (ex, ey)
        return [
            (
                (1 - t) ** 3 * start[0]
                + 3 * (1 - t) ** 2 * t * p1[0]
                + 3 * (1 - t) * t**2 * p2[0]
                + t**3 * end[0],
                (1 - t) ** 3 * start[1]
                + 3 * (1 - t) ** 2 * t * p1[1]
                + 3 * (1 - t) * t**2 * p2[1]
                + t**3 * end[1],
            )
            for t in (step / CURVE_STEPS for step in range(1, CURVE_STEPS + 1))
        ]
    if op == "Q":
        _, p1x, p1y, ex, ey = command
        p1, end = (p1x, p1y), (ex, ey)
        return [
            (
                (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * p1[0] + t**2 * end[0],
                (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * p1[1] + t**2 * end[1],
            )
            for t in (step / CURVE_STEPS for step in range(1, CURVE_STEPS + 1))
        ]
    if op == "A":
        return _arc_points(start, command[1], command[2], command[3], command[4], command[5], (command[6], command[7]))
    raise NativeSvgPipelineError("PATH_COMMAND_UNSUPPORTED", str(op))


def _flatten_commands(commands: list[tuple[Any, ...]]) -> list[list[tuple[float, float]]]:
    subpaths: list[list[tuple[float, float]]] = []
    current: tuple[float, float] | None = None
    start: tuple[float, float] | None = None
    current_subpath: list[tuple[float, float]] | None = None
    for command in commands:
        op = command[0]
        if op == "M":
            if current_subpath and len(current_subpath) >= 2:
                subpaths.append(current_subpath)
            current = (command[1], command[2])
            start = current
            current_subpath = [current]
        elif op == "L":
            if current is None or current_subpath is None:
                raise NativeSvgPipelineError("PATH_SYNTAX_INVALID", str(command))
            current = (command[1], command[2])
            current_subpath.append(current)
        elif op in {"C", "Q", "A"}:
            if current is None or current_subpath is None:
                raise NativeSvgPipelineError("PATH_SYNTAX_INVALID", str(command))
            points = _curve_points(current, command)
            current_subpath.extend(points)
            current = points[-1]
        elif op == "Z":
            if current is None or start is None or current_subpath is None:
                raise NativeSvgPipelineError("PATH_SYNTAX_INVALID", str(command))
            if current_subpath[-1] != start:
                current_subpath.append(start)
            current = start
        else:
            raise NativeSvgPipelineError("PATH_COMMAND_UNSUPPORTED", str(op))
    if current_subpath and len(current_subpath) >= 2:
        subpaths.append(current_subpath)
    if not subpaths:
        raise NativeSvgPipelineError("PATH_EMPTY", "no drawable geometry")
    return subpaths


def _shape_commands(tag: str, attrs: dict[str, str]) -> list[tuple[Any, ...]]:
    if tag == "path":
        return _parse_path_commands(attrs.get("d", "").strip())
    if tag == "rect":
        x = _finite_float(attrs.get("x", "0"), code="SHAPE_GEOMETRY_INVALID", context="x")
        y = _finite_float(attrs.get("y", "0"), code="SHAPE_GEOMETRY_INVALID", context="y")
        width = _finite_float(attrs.get("width", "0"), code="SHAPE_GEOMETRY_INVALID", context="width")
        height = _finite_float(attrs.get("height", "0"), code="SHAPE_GEOMETRY_INVALID", context="height")
        if width <= 0 or height <= 0:
            raise NativeSvgPipelineError("SHAPE_GEOMETRY_INVALID", tag)
        has_rx, has_ry = "rx" in attrs, "ry" in attrs
        rx = _finite_float(attrs.get("rx", "0"), code="SHAPE_GEOMETRY_INVALID", context="rx")
        ry = _finite_float(attrs.get("ry", "0"), code="SHAPE_GEOMETRY_INVALID", context="ry")
        if has_rx and not has_ry:
            ry = rx
        if has_ry and not has_rx:
            rx = ry
        if rx < 0 or ry < 0:
            raise NativeSvgPipelineError("SHAPE_GEOMETRY_INVALID", tag)
        rx, ry = min(rx, width / 2), min(ry, height / 2)
        if rx == 0 or ry == 0:
            return [("M", x, y), ("L", x + width, y), ("L", x + width, y + height), ("L", x, y + height), ("Z",)]
        return [
            ("M", x + rx, y),
            ("L", x + width - rx, y),
            ("A", rx, ry, 0.0, 0, 1, x + width, y + ry),
            ("L", x + width, y + height - ry),
            ("A", rx, ry, 0.0, 0, 1, x + width - rx, y + height),
            ("L", x + rx, y + height),
            ("A", rx, ry, 0.0, 0, 1, x, y + height - ry),
            ("L", x, y + ry),
            ("A", rx, ry, 0.0, 0, 1, x + rx, y),
            ("Z",),
        ]
    if tag in {"circle", "ellipse"}:
        cx = _finite_float(attrs.get("cx", "0"), code="SHAPE_GEOMETRY_INVALID", context="cx")
        cy = _finite_float(attrs.get("cy", "0"), code="SHAPE_GEOMETRY_INVALID", context="cy")
        if tag == "circle":
            rx = ry = _finite_float(attrs.get("r", "0"), code="SHAPE_GEOMETRY_INVALID", context="r")
        else:
            rx = _finite_float(attrs.get("rx", "0"), code="SHAPE_GEOMETRY_INVALID", context="rx")
            ry = _finite_float(attrs.get("ry", "0"), code="SHAPE_GEOMETRY_INVALID", context="ry")
        if rx <= 0 or ry <= 0:
            raise NativeSvgPipelineError("SHAPE_GEOMETRY_INVALID", tag)
        return [
            ("M", cx + rx, cy),
            ("A", rx, ry, 0.0, 0, 1, cx, cy + ry),
            ("A", rx, ry, 0.0, 0, 1, cx - rx, cy),
            ("A", rx, ry, 0.0, 0, 1, cx, cy - ry),
            ("A", rx, ry, 0.0, 0, 1, cx + rx, cy),
            ("Z",),
        ]
    if tag == "line":
        return [
            ("M", _finite_float(attrs.get("x1", "0"), code="SHAPE_GEOMETRY_INVALID", context="x1"), _finite_float(attrs.get("y1", "0"), code="SHAPE_GEOMETRY_INVALID", context="y1")),
            ("L", _finite_float(attrs.get("x2", "0"), code="SHAPE_GEOMETRY_INVALID", context="x2"), _finite_float(attrs.get("y2", "0"), code="SHAPE_GEOMETRY_INVALID", context="y2")),
        ]
    if tag in {"polyline", "polygon"}:
        points = _parse_points(attrs.get("points", ""))
        commands = [("M", *points[0]), *[("L", *point) for point in points[1:]]]
        if tag == "polygon":
            commands.append(("Z",))
        return commands
    raise NativeSvgPipelineError("SVG_ELEMENT_UNSUPPORTED", tag)


def _style_value(el: ET.Element, name: str, inherited: dict[str, Any], *, default: Any) -> Any:
    return el.attrib[name] if name in el.attrib else inherited.get(name, default)


def _parse_style(el: ET.Element, inherited: dict[str, Any]) -> dict[str, Any]:
    fill = _color(_style_value(el, "fill", inherited, default="#000000"), default="#000000")
    stroke = _color(_style_value(el, "stroke", inherited, default="none"), default="none")
    stroke_width = _finite_float(str(_style_value(el, "stroke-width", inherited, default="1")), code="STROKE_WIDTH_INVALID", context="stroke-width")
    fill_opacity = _finite_float(str(_style_value(el, "fill-opacity", inherited, default="1")), code="OPACITY_INVALID", context="fill-opacity")
    stroke_opacity = _finite_float(str(_style_value(el, "stroke-opacity", inherited, default="1")), code="OPACITY_INVALID", context="stroke-opacity")
    opacity = _finite_float(str(_style_value(el, "opacity", inherited, default="1")), code="OPACITY_INVALID", context="opacity")
    stroke_miterlimit = _finite_float(str(_style_value(el, "stroke-miterlimit", inherited, default="4")), code="STYLE_VALUE_INVALID", context="stroke-miterlimit")
    if stroke_width < 0 or fill_opacity < 0 or stroke_opacity < 0 or opacity < 0 or any(x > 1 for x in (fill_opacity, stroke_opacity, opacity)):
        raise NativeSvgPipelineError("STYLE_VALUE_INVALID", el.tag)
    if stroke_miterlimit < 1:
        raise NativeSvgPipelineError("STYLE_VALUE_INVALID", el.tag)
    linecap = str(_style_value(el, "stroke-linecap", inherited, default="butt"))
    linejoin = str(_style_value(el, "stroke-linejoin", inherited, default="miter"))
    fill_rule = str(_style_value(el, "fill-rule", inherited, default="nonzero"))
    if linecap not in {"butt", "round", "square"} or linejoin not in {"miter", "round", "bevel"} or fill_rule not in {"nonzero", "evenodd"}:
        raise NativeSvgPipelineError("STYLE_VALUE_INVALID", el.tag)
    return {
        "fill": fill,
        "stroke": stroke,
        "stroke_width": stroke_width,
        "fill_opacity": fill_opacity,
        "stroke_opacity": stroke_opacity,
        "opacity": inherited.get("opacity", 1.0) * opacity,
        "stroke_linecap": linecap,
        "stroke_linejoin": linejoin,
        "stroke_miterlimit": stroke_miterlimit,
        "fill_rule": fill_rule,
    }


def _validate_attributes(el: ET.Element, tag: str) -> None:
    allowed = (ROOT_ATTRS if tag == "svg" else COMMON_ATTRS) | GEOMETRY_ATTRS.get(tag, set())
    allowed_lower = {candidate.casefold() for candidate in allowed}
    for key, value in el.attrib.items():
        local = _local(key).casefold()
        value = str(value)
        if local.startswith("on"):
            raise NativeSvgPipelineError("SVG_EVENT_HANDLER_FORBIDDEN", local)
        if local in {"href", "src", "style", "font-family"} or URLISH.search(value):
            raise NativeSvgPipelineError("SVG_EXTERNAL_OR_STYLE_FORBIDDEN", f"{local}={value[:100]}")
        if local not in allowed_lower:
            raise NativeSvgPipelineError("SVG_ATTRIBUTE_UNSUPPORTED", local)
        if local == "id" and value and not IDENTIFIER_RE.fullmatch(value):
            raise NativeSvgPipelineError("SVG_ATTRIBUTE_UNSAFE", local)


def _command_endpoints(commands: Iterable[tuple[Any, ...]]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for command in commands:
        if command[0] == "Z":
            continue
        if command[0] == "A":
            points.append((command[6], command[7]))
        else:
            values = command[1:]
            points.append((float(values[-2]), float(values[-1])))
    return points


def _transform_subpaths(subpaths: list[list[tuple[float, float]]], matrix: tuple[float, float, float, float, float, float]) -> list[list[tuple[float, float]]]:
    return [[_apply_matrix(point, matrix) for point in subpath] for subpath in subpaths]


def _flattened_point_count(subpaths: list[list[tuple[float, float]]]) -> int:
    return sum(len(subpath) for subpath in subpaths)


def _bounds(subpaths: list[list[tuple[float, float]]]) -> tuple[float, float, float, float]:
    points = [point for subpath in subpaths for point in subpath]
    return min(point[0] for point in points), min(point[1] for point in points), max(point[0] for point in points), max(point[1] for point in points)


def _canonical_command(command: tuple[Any, ...]) -> str:
    if command[0] == "Z":
        return "Z"
    return command[0] + " " + " ".join(_format_number(float(value)) for value in command[1:])


def _canonical_style(element: dict[str, Any]) -> str:
    values = [
        f'fill="{element["fill"]}"',
        f'stroke="{element["stroke"]}"',
        f'stroke-width="{_format_number(element["stroke_width"])}"',
    ]
    for key, attr in (("fill_opacity", "fill-opacity"), ("stroke_opacity", "stroke-opacity"), ("opacity", "opacity")):
        if element[key] != 1:
            values.append(f'{attr}="{_format_number(element[key])}"')
    if element["stroke_linecap"] != "butt":
        values.append(f'stroke-linecap="{element["stroke_linecap"]}"')
    if element["stroke_linejoin"] != "miter":
        values.append(f'stroke-linejoin="{element["stroke_linejoin"]}"')
    if element["stroke_miterlimit"] != 4:
        values.append(f'stroke-miterlimit="{_format_number(element["stroke_miterlimit"])}"')
    if element["fill_rule"] != "nonzero":
        values.append(f'fill-rule="{element["fill_rule"]}"')
    if element.get("transform"):
        values.append(f'transform="{element["transform"]}"')
    return " ".join(values)


def _canonical_element(element: dict[str, Any]) -> str:
    style = _canonical_style(element)
    tag = element["kind"]
    if tag == "path":
        geometry = "d=\"" + " ".join(_canonical_command(command) for command in element["commands"]) + "\""
    elif tag in {"polyline", "polygon"}:
        geometry = "points=\"" + " ".join(f"{_format_number(x)},{_format_number(y)}" for x, y in element["source_points"]) + "\""
    else:
        geometry = " ".join(f'{key}="{_format_number(value)}"' for key, value in element["geometry"].items())
    return f"<{tag} {geometry} {style}/>"


def _render_dimensions(viewbox: list[float], size: int) -> tuple[float, int, int]:
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0 or size > MAX_RENDER_SIZE:
        raise NativeSvgPipelineError("RENDER_SIZE_INVALID", str(size))
    _, _, width, height = viewbox
    scale = min(size / width, size / height)
    output_width = max(1, int(round(width * scale)))
    output_height = max(1, int(round(height * scale)))
    if output_width * output_height > MAX_RENDER_PIXELS:
        raise NativeSvgPipelineError("RENDER_BOUNDS_EXCEEDED", f"{output_width}x{output_height}")
    return scale, output_width, output_height


def validate_and_normalize(
    svg_text: str,
    *,
    max_bytes: int = 1_048_576,
    max_paths: int = 512,
    max_total_points: int = 8192,
    max_path_chars: int = 32768,
) -> dict[str, Any]:
    raw = svg_text.encode("utf-8")
    if not raw or len(raw) > max_bytes:
        raise NativeSvgPipelineError("SVG_SIZE_INVALID", str(len(raw)))
    low = svg_text.casefold()
    if "<!doctype" in low or "<!entity" in low:
        raise NativeSvgPipelineError("SVG_DTD_FORBIDDEN", "doctype/entity")
    try:
        root = ET.fromstring(svg_text)
    except ET.ParseError as exc:
        raise NativeSvgPipelineError("SVG_XML_INVALID", str(exc)) from exc
    if _local(root.tag) != "svg":
        raise NativeSvgPipelineError("SVG_ROOT_INVALID", root.tag)
    if _namespace(root.tag) not in {None, SVG_NS}:
        raise NativeSvgPipelineError("SVG_NAMESPACE_UNSAFE", root.tag)
    viewbox = root.attrib.get("viewBox")
    if not viewbox:
        raise NativeSvgPipelineError("VIEWBOX_REQUIRED", "missing")
    viewbox_tokens = _parse_number_tokens(viewbox)
    if len(viewbox_tokens) != 4 or any(isinstance(token, str) for token in viewbox_tokens):
        raise NativeSvgPipelineError("VIEWBOX_INVALID", viewbox)
    minx, miny, width, height = [float(token) for token in viewbox_tokens]
    if not all(math.isfinite(value) for value in (minx, miny, width, height)) or width <= 0 or height <= 0 or width > 100000 or height > 100000:
        raise NativeSvgPipelineError("VIEWBOX_INVALID", viewbox)
    _render_dimensions([minx, miny, width, height], 1024)

    xml_nodes = 0
    for element in root.iter():
        xml_nodes += 1
        if xml_nodes > MAX_XML_NODES:
            raise NativeSvgPipelineError("SVG_COMPLEXITY_EXCEEDED", str(xml_nodes))
        if not isinstance(element.tag, str):
            raise NativeSvgPipelineError("SVG_XML_UNSUPPORTED", "non-element node")
        if (element.text or "").strip() or any((child.tail or "").strip() for child in list(element)):
            raise NativeSvgPipelineError("SVG_TEXT_FORBIDDEN", _local(element.tag))
        tag = _local(element.tag)
        if _namespace(element.tag) not in {None, SVG_NS}:
            raise NativeSvgPipelineError("SVG_NAMESPACE_UNSAFE", element.tag)
        if tag in FORBIDDEN_TAGS:
            raise NativeSvgPipelineError("SVG_FORBIDDEN_ELEMENT", tag)
        if tag not in ALLOWED_TAGS:
            raise NativeSvgPipelineError("SVG_ELEMENT_UNSUPPORTED", tag)
        _validate_attributes(element, tag)
    if root.attrib.get("transform"):
        _parse_transform(root.attrib["transform"])

    default_style = _parse_style(root, {})
    if default_style["stroke_width"] > max(width, height):
        raise NativeSvgPipelineError("STROKE_WIDTH_INVALID", str(default_style["stroke_width"]))
    root_matrix = _parse_transform(root.attrib.get("transform"))
    elements: list[dict[str, Any]] = []

    def visit(parent: ET.Element, inherited_style: dict[str, Any], parent_matrix: tuple[float, float, float, float, float, float], depth: int = 0) -> None:
        if depth > MAX_GROUP_DEPTH:
            raise NativeSvgPipelineError("SVG_COMPLEXITY_EXCEEDED", str(depth))
        style = _parse_style(parent, inherited_style)
        if style["stroke_width"] > max(width, height):
            raise NativeSvgPipelineError("STROKE_WIDTH_INVALID", str(style["stroke_width"]))
        matrix = _matrix_multiply(parent_matrix, _parse_transform(parent.attrib.get("transform")))
        tag = _local(parent.tag)
        if tag not in {"svg", "g"}:
            geometry_attrs = {key: value for key, value in parent.attrib.items() if _local(key) in GEOMETRY_ATTRS[tag]}
            if tag == "path" and len(geometry_attrs.get("d", "")) > max_path_chars:
                raise NativeSvgPipelineError("PATH_COMPLEXITY_EXCEEDED", str(len(geometry_attrs["d"])))
            commands = _shape_commands(tag, geometry_attrs)
            local_subpaths = _flatten_commands(commands)
            transformed_subpaths = _transform_subpaths(local_subpaths, matrix)
            raw_points = [_apply_matrix(point, matrix) for point in _command_endpoints(commands)]
            if not raw_points:
                raise NativeSvgPipelineError("PATH_EMPTY", tag)
            all_points = [*raw_points, *[point for subpath in transformed_subpaths for point in subpath]]
            for point in all_points:
                if not all(math.isfinite(value) for value in point):
                    raise NativeSvgPipelineError("PATH_NONFINITE", tag)
                if point[0] < minx or point[1] < miny or point[0] > minx + width or point[1] > miny + height:
                    raise NativeSvgPipelineError("PATH_OUT_OF_BOUNDS", tag)
            if style["stroke"] != "none" and style["stroke_width"] > 0:
                left, top, right, bottom = _bounds(transformed_subpaths)
                half_stroke = style["stroke_width"] / 2
                if left - half_stroke < minx or top - half_stroke < miny or right + half_stroke > minx + width or bottom + half_stroke > miny + height:
                    raise NativeSvgPipelineError("PATH_OUT_OF_BOUNDS", tag)
            point_count = _flattened_point_count(transformed_subpaths)
            if point_count > max_total_points:
                raise NativeSvgPipelineError("PATH_COMPLEXITY_EXCEEDED", str(point_count))
            painted_fill = style["fill"] != "none" and style["fill_opacity"] > 0
            painted_stroke = style["stroke"] != "none" and style["stroke_opacity"] > 0
            visible = style["opacity"] > 0 and (painted_stroke if tag == "line" else painted_fill or painted_stroke)
            if not visible:
                raise NativeSvgPipelineError("INVISIBLE_PATH", tag)
            geometry: dict[str, float] = {}
            source_points: list[tuple[float, float]] = []
            if tag == "rect":
                for key in ("x", "y", "width", "height"):
                    geometry[key] = _finite_float(geometry_attrs.get(key, "0"), code="SHAPE_GEOMETRY_INVALID", context=key)
                for key in ("rx", "ry"):
                    if key in geometry_attrs:
                        geometry[key] = _finite_float(geometry_attrs[key], code="SHAPE_GEOMETRY_INVALID", context=key)
            elif tag == "circle":
                for key in ("cx", "cy", "r"):
                    geometry[key] = _finite_float(geometry_attrs.get(key, "0"), code="SHAPE_GEOMETRY_INVALID", context=key)
            elif tag == "ellipse":
                for key in ("cx", "cy", "rx", "ry"):
                    geometry[key] = _finite_float(geometry_attrs.get(key, "0"), code="SHAPE_GEOMETRY_INVALID", context=key)
            elif tag == "line":
                for key in ("x1", "y1", "x2", "y2"):
                    geometry[key] = _finite_float(geometry_attrs.get(key, "0"), code="SHAPE_GEOMETRY_INVALID", context=key)
            elif tag in {"polyline", "polygon"}:
                source_points = _parse_points(geometry_attrs.get("points", ""))
            transform = _format_transform(matrix)
            elements.append({
                "kind": tag,
                "commands": commands,
                "subpaths": transformed_subpaths,
                "points": [point for subpath in transformed_subpaths for point in subpath],
                "fill": style["fill"],
                "stroke": style["stroke"],
                "stroke_width": style["stroke_width"],
                "fill_opacity": style["fill_opacity"],
                "stroke_opacity": style["stroke_opacity"],
                "opacity": style["opacity"],
                "stroke_linecap": style["stroke_linecap"],
                "stroke_linejoin": style["stroke_linejoin"],
                "stroke_miterlimit": style["stroke_miterlimit"],
                "fill_rule": style["fill_rule"],
                "geometry": geometry,
                "source_points": source_points,
                "transform": transform,
            })
            return
        for child in list(parent):
            visit(child, style, matrix, depth + 1)

    # Parse root styles once, then traverse children so root opacity/transform is not duplicated.
    for child in list(root):
        visit(child, default_style, root_matrix)
    if not elements:
        raise NativeSvgPipelineError("VECTOR_GEOMETRY_REQUIRED", "none")
    if len(elements) > max_paths:
        raise NativeSvgPipelineError("PATH_COUNT_EXCEEDED", str(len(elements)))
    total_points = sum(len(element["points"]) for element in elements)
    if total_points > max_total_points:
        raise NativeSvgPipelineError("PATH_COMPLEXITY_EXCEEDED", str(total_points))

    canonical_body = "".join(_canonical_element(element) for element in elements)
    canonical = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{_format_number(minx)} {_format_number(miny)} {_format_number(width)} {_format_number(height)}">{canonical_body}</svg>'
    result: dict[str, Any] = {
        "schema": "die.factory-asset.native-svg-safe.v1",
        "viewbox": [minx, miny, width, height],
        "elements": elements,
        "paths": [element for element in elements if element["kind"] == "path"],
        "shapes": [element for element in elements if element["kind"] != "path"],
        "path_count": sum(element["kind"] == "path" for element in elements),
        "geometry_count": len(elements),
        "shape_count": sum(element["kind"] != "path" for element in elements),
        "total_points": total_points,
        "canonical_svg": canonical,
        "canonical_svg_sha256": sha256_bytes(canonical.encode()),
        "native_editable": True,
        "generated_by_native_producer": True,
        "conversion_from_raster": False,
    }
    image = render_png_image(result, size=512)
    pixels = image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata()
    ink = sum(1 for pixel in pixels if pixel[:3] != (255, 255, 255))
    if ink < 16:
        raise NativeSvgPipelineError("BLANK_OR_NEAR_BLANK_OUTPUT", str(ink))
    result["render_ink_pixels_512"] = ink
    return result


def _flattened_elements(norm: dict[str, Any]) -> list[dict[str, Any]]:
    if "elements" in norm:
        return norm["elements"]
    return norm.get("paths", [])


def _opaque_rgb(color: str, opacity: float) -> tuple[int, int, int]:
    rgb = _rgb(color)
    return tuple(max(0, min(255, int(round(255 - (255 - channel) * opacity)))) for channel in rgb)


def render_png_image(norm: dict[str, Any], *, size: int = 1024) -> Image.Image:
    scale, output_width, output_height = _render_dimensions(norm["viewbox"], size)
    minx, miny, _, _ = norm["viewbox"]
    image = Image.new("RGB", (output_width, output_height), "white")
    draw = ImageDraw.Draw(image)
    for element in _flattened_elements(norm):
        fill_opacity = element.get("fill_opacity", 1.0) * element.get("opacity", 1.0)
        stroke_opacity = element.get("stroke_opacity", 1.0) * element.get("opacity", 1.0)
        fill = element.get("fill", "#000000")
        stroke = element.get("stroke", "none")
        for subpath in element.get("subpaths", [element.get("points", [])]):
            points = [((x - minx) * scale, (y - miny) * scale) for x, y in subpath]
            if len(points) < 2:
                continue
            if fill != "none" and fill_opacity > 0 and len(points) >= 3:
                draw.polygon(points, fill=_opaque_rgb(fill, fill_opacity))
            if stroke != "none" and stroke_opacity > 0:
                width = max(1, int(round(element.get("stroke_width", 1) * scale)))
                draw.line(points, fill=_opaque_rgb(stroke, stroke_opacity), width=width, joint=element.get("stroke_linejoin", "curve"))
    return image


def png_bytes(norm: dict[str, Any], *, size: int = 1024) -> bytes:
    buffer = io.BytesIO()
    render_png_image(norm, size=size).save(buffer, format="PNG", optimize=False)
    return buffer.getvalue()


def jpeg_bytes(norm: dict[str, Any], *, size: int = 1024) -> bytes:
    buffer = io.BytesIO()
    render_png_image(norm, size=size).save(buffer, format="JPEG", quality=95, subsampling=0, optimize=False, progressive=False)
    return buffer.getvalue()


def _eps_subpath_lines(subpath: list[tuple[float, float]], *, minx: float, miny: float, height: float) -> list[str]:
    x0, y0 = subpath[0]
    lines = ["newpath", f"{x0 - minx:.3f} {height - (y0 - miny):.3f} moveto"]
    for x, y in subpath[1:]:
        lines.append(f"{x - minx:.3f} {height - (y - miny):.3f} lineto")
    if len(subpath) >= 3 and subpath[-1] == subpath[0]:
        lines.append("closepath")
    return lines


def eps_bytes(norm: dict[str, Any]) -> bytes:
    minx, miny, width, height = norm["viewbox"]
    lines = [
        "%!PS-Adobe-3.0 EPSF-3.0",
        f"%%BoundingBox: 0 0 {int(math.ceil(width))} {int(math.ceil(height))}",
        "1 setlinejoin",
        "1 setlinecap",
    ]
    for element in _flattened_elements(norm):
        for subpath in element.get("subpaths", [element.get("points", [])]):
            if len(subpath) < 2:
                continue
            path_lines = _eps_subpath_lines(subpath, minx=minx, miny=miny, height=height)
            if element.get("fill", "none") != "none" and len(subpath) >= 3:
                r, g, b = _rgb(element["fill"])
                lines.extend(path_lines)
                lines.extend([f"{r / 255:.6f} {g / 255:.6f} {b / 255:.6f} setrgbcolor", "fill"])
            if element.get("stroke", "none") != "none":
                r, g, b = _rgb(element["stroke"])
                lines.extend(path_lines)
                lines.extend([
                    f"{element.get('stroke_width', 1):.3f} setlinewidth",
                    f"{r / 255:.6f} {g / 255:.6f} {b / 255:.6f} setrgbcolor",
                    "stroke",
                ])
    lines += ["showpage", "%%EOF"]
    return ("\n".join(lines) + "\n").encode("ascii")


def package_svg_master(*, svg_text: str, semantic_asset_id: str, blueprint_sha256: str, provider_prompt_sha256: str) -> dict[str, Any]:
    normalized = validate_and_normalize(svg_text)
    svg = normalized["canonical_svg"].encode()
    eps = eps_bytes(normalized)
    png = png_bytes(normalized)
    jpg = jpeg_bytes(normalized)
    master = {
        "format": "SVG",
        "bytes": len(svg),
        "sha256": sha256_bytes(svg),
        "native_editable": True,
        "generated_by_native_producer": True,
        "conversion_from_raster": False,
        "lineage_sha256_required": True,
    }
    derivatives = []
    for derivative_id, fmt, purpose, data in [
        ("ADOBE_EPS", "EPS", "MARKETPLACE_DELIVERY", eps),
        ("PNG_PREVIEW", "PNG", "PREVIEW", png),
        ("JPEG_PREVIEW", "JPEG", "PREVIEW", jpg),
    ]:
        derivatives.append({
            "derivative_id": derivative_id,
            "format": fmt,
            "purpose": purpose,
            "bytes": len(data),
            "sha256": sha256_bytes(data),
            "semantic_identity_effect": "NONE",
        })
    package = {
        "schema": "die.factory-asset.native-svg-package.v1",
        "semantic_asset_id": semantic_asset_id,
        "blueprint_sha256": blueprint_sha256,
        "provider_prompt_sha256": provider_prompt_sha256,
        "master": master,
        "derivatives": derivatives,
        "semantic_asset_count": 1,
        "derivatives_create_new_semantic_asset": False,
        "qa": {
            "path_count": normalized["path_count"],
            "geometry_count": normalized["geometry_count"],
            "shape_count": normalized["shape_count"],
            "total_points": normalized["total_points"],
            "render_ink_pixels_512": normalized["render_ink_pixels_512"],
            "independent_render": "PIL_FROM_PARSED_VECTOR_GEOMETRY",
        },
    }
    package["package_sha256"] = sha256_value(package)
    return {"package": package, "normalized": normalized, "bytes": {"SVG": svg, "EPS": eps, "PNG": png, "JPEG": jpg}}
