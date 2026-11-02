"""A small reader for the subset of Unity's YAML that the game's level assets use (stdlib only).

Block mappings, block sequences (Unity writes a list's "- " at its key's own indent), plain scalars and the empty
forms `key: []` and `key:`. Everything is returned as str / dict / list; the caller converts numbers.
"""


def _lead(line):
    return len(line) - len(line.lstrip(" "))


def _parse_map(lines, i, ind):
    d = {}
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        lead = _lead(line)
        content = line.strip()
        if lead < ind or (lead == ind and content.startswith("- ")) or content == "-":
            break
        if lead > ind:  # a wrapped scalar continuation: append to the last key
            if d:
                k = list(d)[-1]
                if isinstance(d[k], str):
                    d[k] += " " + content
            i += 1
            continue
        key, _, val = content.partition(":")
        val = val.strip()
        i += 1
        if val == "":
            # a nested block, a list at the same indent, or an empty value
            j = i
            while j < n and not lines[j].strip():
                j += 1
            if j < n:
                nl, nc = _lead(lines[j]), lines[j].strip()
                if nc.startswith("- ") and nl >= ind:
                    d[key], i = _parse_seq(lines, j, nl)
                    continue
                if nl > ind:
                    d[key], i = _parse_map(lines, j, nl)
                    continue
            d[key] = ""
        elif val == "[]":
            d[key] = []
        else:
            d[key] = val
    return d, i


def _parse_seq(lines, i, ind):
    items = []
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        lead = _lead(line)
        content = line.strip()
        if lead != ind or not content.startswith("- "):
            break
        rest = content[2:]
        if ":" in rest and not rest.startswith("{"):
            lines = lines[:i] + [" " * (ind + 2) + rest] + lines[i + 1:]
            item, i = _parse_map(lines, i, ind + 2)
            items.append(item)
        else:
            items.append(rest)
            i += 1
    return items, i


def load(text):
    """The MonoBehaviour body of one asset (the mapping under `MonoBehaviour:`)."""
    lines = [ln for ln in text.splitlines() if not ln.startswith("%") and not ln.startswith("---")]
    root, _ = _parse_map(lines, 0, 0)
    return root.get("MonoBehaviour", root)
