#!/usr/bin/env python3
"""Merge AutoProxy upstream rules into proxy.list and deduplicate.

Existing proxy.list entries are kept; the result is written back to the same file.

Usage: merge.py <upstream_autoproxy.txt> <proxy.list>
"""
import re
import sys

SECTIONS = ("domain_suffix", "exact", "regex")


def host_of(rule):
    """Extract the host part of an AutoProxy rule."""
    rule = re.sub(r"^\|?https?://", "", rule.lstrip("|"))
    return re.split(r"[/^:]", rule, 1)[0].strip(".").lower()


def wildcard_to_regex(host):
    return r"(^|\.)" + host.replace(".", r"\.").replace("*", "[^.]*") + "$"


def parse_upstream(path, out):
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        # Skip header, comments, blank lines and @@ allowlist rules (sections cannot express exclusions)
        if not line or line.startswith(("[", "!", "@@")):
            continue
        if line.startswith("/") and line.endswith("/"):
            # The only URL regex: /^https?:\/\/[^\/]+blogspot\.(.*)/ -> host regex
            if "blogspot" in line:
                out["regex"].add(r".+blogspot\..+$")
            else:
                print(f"skip unsupported regex: {line}", file=sys.stderr)
            continue
        host = host_of(line)
        if not host:
            continue
        if "*" in host:
            out["regex"].add(wildcard_to_regex(host))
        elif line.startswith("|") and not line.startswith("||"):
            out["exact"].add(host)  # |http://host matches this host only
        else:
            out["domain_suffix"].add(host)  # ||host and bare keywords are treated as suffixes


def parse_sections(path, out):
    section = None
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line.startswith("## "):
            section = re.match(r"\s*([a-z_]*)", line[3:]).group(1)
            continue
        if not line or line.startswith("#"):
            continue
        if section not in SECTIONS:
            sys.exit(f"{path}: entry outside known section: {line}")
        out[section].add(line if section == "regex" else line.lower())


def covered(host, suffixes, include_self):
    parts = host.split(".")
    start = 0 if include_self else 1
    return any(".".join(parts[i:]) in suffixes for i in range(start, len(parts)))


def main(upstream, list_path):
    rules = {s: set() for s in SECTIONS}
    parse_upstream(upstream, rules)
    parse_sections(list_path, rules)

    # Entries covered by a parent suffix are redundant
    suffix = rules["domain_suffix"]
    suffix = {h for h in suffix if not covered(h, suffix, include_self=False)}
    exact = {h for h in rules["exact"] if not covered(h, suffix, include_self=True)}
    result = {"domain_suffix": suffix, "exact": exact, "regex": rules["regex"]}

    with open(list_path, "w", encoding="utf-8") as f:
        f.write("# skylinevpn-proxylist\n")
        f.write("# License: Skyline Networking Tech LLC\n")
        for s in SECTIONS:
            f.write(f"\n## {s}\n")
            f.writelines(f"{h}\n" for h in sorted(result[s]))

    print(", ".join(f"{s}={len(result[s])}" for s in SECTIONS))


if __name__ == "__main__":
    main(*sys.argv[1:3])
