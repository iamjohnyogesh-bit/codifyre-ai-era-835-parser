"""Low-level X12 EDI utilities: delimiter detection, segment splitting, envelopes."""

from dataclasses import dataclass, field


@dataclass
class Transaction:
    """One ST..SE transaction set with its segments (each a list of elements)."""
    set_id: str            # ST01, e.g. "835"
    control: str           # ST02
    segments: list = field(default_factory=list)  # includes ST and SE


@dataclass
class Delimiters:
    element: str = "*"
    component: str = "^"
    segment: str = "~"


def detect_delimiters(text):
    """Learn delimiters from the ISA header (element separator is ISA[3];
    ISA16 is the component separator; the next char ends the segment)."""
    idx = text.find("ISA")
    if idx < 0 or len(text) < idx + 4:
        return Delimiters()
    sep = text[idx + 3]
    pos = idx
    for _ in range(16):
        pos = text.find(sep, pos + 1) if pos != idx else idx + 3
        if pos < 0:
            return Delimiters(element=sep)
    if len(text) < pos + 3:
        return Delimiters(element=sep)
    return Delimiters(element=sep, component=text[pos + 1], segment=text[pos + 2])


def split_segments(text):
    """Return (delimiters, segments) where segments is a list of element lists."""
    d = detect_delimiters(text)
    raw = []
    if text.find("ISA") >= 0:
        raw = [x.strip() for x in text.split(d.segment) if x.strip()]
    else:
        raw = [x.strip().rstrip("~") for x in text.replace("\r", "").split("\n") if x.strip()]
    segments = [seg.split(d.element) for seg in raw]
    return d, segments


def iter_transactions(segments):
    """Yield Transaction objects for every ST..SE block in the stream."""
    current = None
    for seg in segments:
        if seg[0] == "ST":
            current = Transaction(set_id=seg[1] if len(seg) > 1 else "",
                                  control=seg[2] if len(seg) > 2 else "",
                                  segments=[seg])
        elif seg[0] == "SE":
            if current is not None:
                current.segments.append(seg)
                yield current
                current = None
        elif current is not None:
            current.segments.append(seg)


def el(seg, idx, default=""):
    """Safe element access."""
    return seg[idx] if len(seg) > idx and seg[idx] != "" else default


def num(s, default=0.0):
    try:
        return float(s)
    except (TypeError, ValueError):
        return default


def money(s):
    return round(num(s), 2)
