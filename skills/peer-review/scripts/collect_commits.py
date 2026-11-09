#!/usr/bin/env python3
"""Collect teammates' commits on a shared remote branch since the last review, group them by
author, and run mechanical format checks. Also stores the review position and open findings.

Usage (from anywhere inside the repo; output is Markdown on stdout):
  python3 -I collect_commits.py [options]

Options
  --base <SHA>      Only commits after this one (default: last reviewed SHA in the state file, else --days)
  --days <N>        Period to look at when there is no usable state (default 7)
  --self <name>     Author to exclude (default: git config user.name)
  --include-self    Include your own commits too
  --no-fetch        Do not run git fetch
  --mark <SHA>      Record this remote SHA as reviewed, then exit
  --findings-add <JSON file>
                    Add findings to the open list, then exit
                    (fields: author, commit, file, severity, label, summary)
  --close <ID> ...  Close open findings, then exit (--reason fixed|withdrawn, default fixed)

Config: .devkit/peer-review/config.json (optional; see references/config.md).
State:  .devkit/peer-review/state.json
Only the commit format is checked here. Code content is not read.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

CONF_DIR = os.path.join(".devkit", "peer-review")
CONFIG_PATH = os.path.join(CONF_DIR, "config.json")
STATE_PATH = os.path.join(CONF_DIR, "state.json")

TRAILER_RE = re.compile(r"^(Co-Authored-By|Signed-off-by|Generated with|🤖)", re.I)
# If at least this share of deleted lines changed only whitespace, suspect a reformat
WS_ONLY_RATIO = 0.4
WS_MIN_LINES = 20  # small changes make the ratio noisy, so skip them


def git(*args, check=True):
    r = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        sys.exit(f"[stop] git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return None
    except ValueError as e:
        sys.exit(f"[stop] {path} is not valid JSON: {e}")


def save_state(st):
    os.makedirs(CONF_DIR, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)


def default_branch(remote):
    prefix = f"refs/remotes/{remote}/"
    ref = git("symbolic-ref", "-q", f"{prefix}HEAD", check=False).strip()
    if ref.startswith(prefix):
        return ref[len(prefix):]
    # origin/HEAD is unset in some clones: take the first common default branch that exists locally
    for name in ("main", "master"):
        if git("rev-parse", "-q", "--verify", prefix + name, check=False).strip():
            return name
    sys.exit(f"[stop] cannot tell the default branch of {remote}. Set `branch` in {CONFIG_PATH}.")


class Rules:
    def __init__(self, cfg):
        cfg = cfg or {}
        self.remote = cfg.get("remote", "origin")
        self.branch = cfg.get("branch") or default_branch(self.remote)
        self.ref = f"refs/remotes/{self.remote}/{self.branch}"
        self.areas = cfg.get("areas", [])
        self.default_area = cfg.get("default_area", "other")
        subj = cfg.get("subject") or {}
        self.subject_re = re.compile(subj["pattern"]) if subj.get("pattern") else None
        self.types = set(subj.get("types", []))
        self.scopes = set(subj.get("scopes", []))
        self.scope_sep = subj.get("scope_separator", ",")
        self.scope_matches_area = subj.get("scope_matches_area", False)
        self.no_period = subj.get("no_period", False)
        self.forbidden_endings = subj.get("forbidden_endings", [])
        body = cfg.get("body") or {}
        self.body_max = body.get("max_lines")
        self.body_bullet = body.get("bullet")
        self.forbid_trailers = cfg.get("forbid_trailers", False)
        self.forbidden_paths = cfg.get("forbidden_paths", [])
        self.no_mix = cfg.get("no_mix", [])
        self.type_path = cfg.get("type_path", [])
        self.revert_markers = ["Revert", *cfg.get("revert_markers", [])]
        self.configured = bool(cfg)

    def area(self, path):
        for a in self.areas:
            if path.startswith(a["prefix"]):
                return a["name"]
        return self.default_area

    def area_scope(self, name):
        for a in self.areas:
            if a["name"] == name:
                return a.get("scope", name)
        return name


def note(item):
    msg = item["message"]
    return ("judgment: " + msg) if item.get("judgment") else msg


def numstat(sha, *flags):
    """(added, deleted, path) per file. -z keeps non-ASCII paths unquoted; a rename yields its new path."""
    toks = git("show", "--format=", "--numstat", "-z", *flags, sha).split("\0")
    rows, i = [], 0
    while i < len(toks):
        parts = toks[i].lstrip("\n").split("\t")
        i += 1
        if len(parts) != 3:
            continue
        path = parts[2]
        if path == "":  # rename/copy: the old and new paths follow as separate tokens
            path, i = toks[i + 1], i + 2
        add = int(parts[0]) if parts[0].isdigit() else 0
        dele = int(parts[1]) if parts[1].isdigit() else 0
        rows.append((add, dele, path))
    return rows


def deleted(sha, *flags):
    return sum(d for _, d, _ in numstat(sha, *flags))


def line_notes(sha, files):
    """Line-ending-only and whitespace-only changes, without counting a CRLF/LF conversion twice."""
    notes = []
    dele = sum(d for _, d, _ in files)
    if not dele:
        return notes
    # Existing CRLF files have a CR on every changed line, so count lines where only the trailing CR differs
    dele_cr = deleted(sha, "--ignore-cr-at-eol")
    if dele - dele_cr:
        notes.append(f"{dele - dele_cr} line(s) changed only the line ending (CR) — CRLF/LF conversion")
    if dele_cr >= WS_MIN_LINES:
        ws = dele_cr - deleted(sha, "-w")  # -w also ignores CR, so measure against the CR-ignored count
        if ws / dele_cr >= WS_ONLY_RATIO:
            notes.append(f"{ws} of {dele_cr} deleted lines ({ws / dele_cr:.0%}) changed only whitespace — possible reformat")
    return notes


def check_commit(R, subject, body, files):
    issues = []
    if body.startswith("\x00no-blank\n"):
        body = body[len("\x00no-blank\n"):]
        issues.append("no blank line after the subject, so the body is glued to it")
    areas = {R.area(p) for _, _, p in files}
    paths = [p for _, _, p in files]
    ctype, desc = None, subject
    m = R.subject_re.match(subject) if R.subject_re else None
    if R.subject_re and not m:
        issues.append("subject does not match the configured format")
    if m:
        gd = m.groupdict()
        ctype, desc = gd.get("type"), gd.get("desc") or subject
        if ctype and R.types and ctype not in R.types:
            issues.append(f"type `{ctype}` is not an allowed type")
        if gd.get("scope") and R.scopes:
            scopes = {s.strip() for s in gd["scope"].split(R.scope_sep)}
            if not scopes <= R.scopes:
                issues.append(f"scope `{gd['scope']}` has a value that is not allowed")
            elif R.scope_matches_area:
                expected = {R.area_scope(a) for a in areas}
                if expected and scopes != expected:
                    issues.append(f"scope `{gd['scope']}` differs from the changed areas `{','.join(sorted(expected))}`")
    desc = desc.rstrip()
    if R.no_period and desc.endswith("."):
        issues.append("subject ends with a period")
    for e in R.forbidden_endings:
        if desc.endswith(e["ending"]):
            issues.append(note(e))
    for tp in R.type_path:
        if ctype == tp["type"] and any(p.startswith(tp["prefix"]) for p in paths):
            issues.append(note(tp))
    body_lines = [l for l in body.splitlines() if l.strip()]
    trailers = [l for l in body_lines if TRAILER_RE.match(l.strip())]
    if R.forbid_trailers and trailers:
        issues.append("trailer or AI attribution: " + "; ".join(trailers))
    plain = [l for l in body_lines if l not in trailers]
    if R.body_max is not None and len(plain) > R.body_max:
        issues.append(f"body has {len(plain)} lines (limit {R.body_max})")
    if R.body_bullet and plain and not all(l.lstrip().startswith(R.body_bullet) for l in plain):
        issues.append(f"body lines are not `{R.body_bullet}` bullets")
    for mix in R.no_mix:
        if set(mix["areas"]) <= areas:
            issues.append(note(mix))
    for fp in R.forbidden_paths:
        if any(p.startswith(fp["prefix"]) for p in paths):
            issues.append(note(fp))
    return issues


def is_ancestor(R, sha):
    return bool(sha) and subprocess.run(
        ["git", "merge-base", "--is-ancestor", sha, R.ref], capture_output=True).returncode == 0


def mark(R, sha):
    full = git("rev-parse", sha).strip()
    if not is_ancestor(R, full):
        sys.exit(f"[stop] {sha} is not in the remote {R.branch} history. Fetch, then record the remote SHA again.")
    st = load_json(STATE_PATH) or {}
    st.update(reviewed_head=full, reviewed_at=datetime.date.today().isoformat())
    save_state(st)
    print(f"recorded: {STATE_PATH} <- {full[:10]}")


def findings_add(R, path):
    items = load_json(path)
    if not isinstance(items, list):
        sys.exit(f"[stop] {path} must hold a JSON list of findings")
    need = ("author", "commit", "file", "severity", "label", "summary")
    st = load_json(STATE_PATH) or {}
    fs = st.setdefault("findings", [])
    n = max((int(x["id"][1:]) for x in fs), default=0)
    head = git("rev-parse", R.ref).strip()
    today = datetime.date.today().isoformat()
    for it in items:
        miss = [k for k in need if not it.get(k)]
        if miss:
            sys.exit(f"[stop] item is missing {', '.join(miss)}: {it}")
        n += 1
        fs.append({"id": f"F{n}", **{k: it[k] for k in need}, "status": "open",
                   "raised_at": today, "raised_head": head})
        print(f"added: F{n} {it['author']} {it['file']} — {it['summary']}")
    save_state(st)


def findings_close(ids, reason):
    st = load_json(STATE_PATH) or {}
    known = {f["id"]: f for f in st.get("findings", [])}
    for i in ids:
        f = known.get(i)
        if not f:
            sys.exit(f"[stop] no finding {i}")
        f.update(status="closed", reason=reason, closed_at=datetime.date.today().isoformat())
        print(f"closed: {i} ({reason})")
    save_state(st)


def print_open_findings(R, st):
    open_fs = [f for f in (st or {}).get("findings", []) if f["status"] == "open"]
    if not open_fs:
        return
    print(f"## Open findings from earlier reviews — {len(open_fs)}\n")
    print("Recheck each. Close fixed ones with `--close <ID>`, non-issues with `--close <ID> --reason withdrawn`.\n")
    for f in open_fs:
        path = f["file"].split(":")[0]
        since = f.get("raised_head")
        touched = ""
        if is_ancestor(R, since):
            hs = [h for h in git("log", "--format=%h %an", f"{since}..{R.ref}", "--", path, check=False).split("\n") if h]
            touched = (f" — file changed {len(hs)} time(s) since ({', '.join(hs[:3])})" if hs
                       else " — file unchanged since")
        print(f"- `{f['id']}` [{f['severity']}·{f['label']}] {f['author']} `{f['commit'][:7]}` "
              f"`{f['file']}` {f['summary']} _(raised {f['raised_at']}{touched})_")
    print()


def merge_kind(subject):
    if re.search(r"into '[^']+'", subject):
        return "GitLab MR merge"
    if subject.startswith("Merge pull request #"):
        return "GitHub PR merge"
    if "remote-tracking" in subject:
        return "pull merge"
    return "direct merge"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--self", dest="self_name")
    ap.add_argument("--include-self", action="store_true")
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--mark")
    ap.add_argument("--findings-add")
    ap.add_argument("--close", nargs="+")
    ap.add_argument("--reason", default="fixed", choices=["fixed", "withdrawn"])
    a = ap.parse_args()

    top = git("rev-parse", "--show-toplevel", check=False).strip()
    if not top:
        sys.exit("[stop] not inside a Git repository.")
    os.chdir(top)
    R = Rules(load_json(CONFIG_PATH))
    if not a.no_fetch:
        # `+` lets the ref follow a force-push; the state check below then falls back to --days
        git("fetch", "--no-tags", "-q", R.remote, f"+refs/heads/{R.branch}:{R.ref}")
    if not git("rev-parse", "-q", "--verify", R.ref, check=False).strip():
        sys.exit(f"[stop] {R.ref} does not exist. Set `branch` in {CONFIG_PATH} or fetch first.")
    if a.mark:
        return mark(R, a.mark)
    if a.findings_add:
        return findings_add(R, a.findings_add)
    if a.close:
        return findings_close(a.close, a.reason)

    head = git("rev-parse", R.ref).strip()
    st = load_json(STATE_PATH)
    base, base_note = a.base, "given"
    if not base and st and is_ancestor(R, st.get("reviewed_head")):
        base, base_note = st["reviewed_head"], f"end of last review ({st.get('reviewed_at')})"
    if base:
        rng, since = [f"{base}..{R.ref}"], []
    else:
        rng, since = [R.ref], [f"--since={a.days} days ago"]
        base_note = f"no usable record → last {a.days} days"
        if st and st.get("reviewed_head"):
            base_note += f" (recorded {st['reviewed_head'][:10]} is not in the remote history)"
    self_name = a.self_name or git("config", "user.name", check=False).strip()

    fmt = "%H%x1f%an%x1f%ad%x1f%s%x1f%b%x1f%B%x1e"
    raw = git("log", *rng, *since, "--no-merges", "--date=short", f"--format={fmt}")
    commits = []
    for rec in raw.split("\x1e"):
        rec = rec.strip("\n")
        if not rec:
            continue
        sha, author, date, subject, body, full_msg = rec.split("\x1f")
        if author == self_name and not a.include_self:
            continue
        first_para = full_msg.strip("\n").split("\n\n")[0]
        if "\n" in first_para:
            # %s joins the first paragraph into one line, so keep only its first line as the subject
            lines = first_para.split("\n")
            subject = lines[0]
            body = "\x00no-blank\n" + "\n".join(lines[1:]) + "\n" + body
        commits.append((sha, author, date, subject, body))
    merges = git("log", *rng, *since, "--merges", "--date=short", "--format=%h%x1f%an%x1f%s")

    print("# Peer review targets\n")
    print(f"- Remote {R.branch}: `{head[:10]}` (full `{head}`)")
    print(f"- Start: {base_note}" + (f" `{base[:10]}`" if base else ""))
    print(f"- Excluded author: {'none' if a.include_self else self_name}")
    print(f"- Config: {CONFIG_PATH if R.configured else 'none — only generic checks ran'}")
    print(f"- Commits: {len(commits)} (merges excluded)\n")
    print_open_findings(R, st)
    if not commits:
        print("No commits to review.")
        return

    by_author = {}
    for c in commits:
        by_author.setdefault(c[1], []).append(c)
    for author, cs in by_author.items():
        tot_a = tot_d = 0
        print(f"## {author} — {len(cs)}\n")
        for sha, _, date, subject, body in reversed(cs):
            files = numstat(sha)
            add, dele = sum(f[0] for f in files), sum(f[1] for f in files)
            tot_a, tot_d = tot_a + add, tot_d + dele
            areas = ",".join(sorted({R.area(p) for _, _, p in files}))
            print(f"- `{sha[:7]}` {date} {subject}  _(+{add} -{dele}, {areas}, {len(files)} files)_")
            notes = check_commit(R, subject, body, files) + line_notes(sha, files)
            for n in notes:
                print(f"  - ⚠️ {n}")
        print(f"\n  Total +{tot_a} -{tot_d}\n")

    rows = []
    for line in merges.splitlines():
        h, au, s = line.split("\x1f")
        if au == self_name and not a.include_self:
            continue
        rows.append(f"- `{h}` {au} {s} — {merge_kind(s)}")
    if rows:
        print("## Merge commits (reference)\n")
        print("\n".join(rows))
    reverts = [c for c in commits if any(m.lower() in c[3].lower() for m in R.revert_markers)]
    if reverts:
        print("\n## Revert commits (reference)\n")
        for sha, au, _, s, _ in reverts:
            print(f"- `{sha[:7]}` {au} {s}")


if __name__ == "__main__":
    main()
