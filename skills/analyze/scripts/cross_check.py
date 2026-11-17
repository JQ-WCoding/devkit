"""Check one cross-check run and render its results, so the evidence rules hold by code, not by prose.

Usage:
  python3 -I cross_check.py check <cross-check dir> [--repo <repo root>]

<cross-check dir> (`<work>/<task>/cross-check/`) holds:
  plan.json                 items, lanes (lane map) and max_rounds, written by the central session
  sources/<lane>/...        exported non-repo material (src:<lane>/<file>, query:<id> -> query-<id>.md)
  round-<n>/lane-<name>.json   one lane analyst's reply, saved verbatim
  round-<n>/compare.json       the comparator's reply
  answers.json              optional: human answers from the gate (verbatim + interpretation)
Writes results.md, questions.md and not-rules.md into <cross-check dir>. The last stdout line is
`STOP: yes (<reason>)` or `STOP: no (<k> open items)`. Exit 0 = valid, 1 = invalid input (fix and rerun), 2 = usage.
The JSON shapes are documented in ../references/cross-check.md.
"""
import argparse
import fnmatch
import json
import os
import re
import sys

SIDES = {'should': {'decision', 'agreement', 'inference'},  # intent lanes never read current state
         'is': {'observed', 'inference'}}                 # current-state lanes cannot produce intent
TYPES = {'decision', 'agreement', 'observed', 'inference'}
INTENT = {'decision', 'agreement'}
STATUSES = ('match', 'mismatch', 'insufficient')
MIN_LANES, MAX_LANES = 2, 3          # 2 by default; a third lane costs one more subagent per round
DEFAULT_MAX_ROUNDS = 3               # source requirement R5
PATH_REF = re.compile(r'^(?P<path>[^\s:#]+):(?P<line>\d+)(-(?P<end>\d+))?$')
SRC_REF = re.compile(r'^src:(?P<lane>[\w-]+)/(?P<file>[^#\s]+)(#\S*)?$')
QUERY_REF = re.compile(r'^query:(?P<id>[\w.-]+)$')
RUN_REF = re.compile(r'^run:(?P<path>\S+)$')
ROUND_DIR = re.compile(r'^round-(\d+)$')


class Invalid(Exception):
    pass


def load(path, what):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise Invalid(f'{what} missing: {path}')
    except json.JSONDecodeError as e:
        raise Invalid(f'{what} is not valid JSON ({path}: {e}). Save the agent reply\'s JSON block verbatim')


def literal_prefix(pattern):
    m = re.search(r'[*?\[]', pattern)
    return pattern[:m.start()] if m else pattern


def check_plan(plan):
    items = plan.get('items')
    lanes = plan.get('lanes')
    if not isinstance(items, list) or not items:
        raise Invalid('plan.json needs a non-empty "items" list of {"id", "text"}')
    ids = [str(i.get('id')) for i in items]
    if len(set(ids)) != len(ids):
        raise Invalid('plan.json item ids must be unique')
    if not isinstance(lanes, list) or not MIN_LANES <= len(lanes) <= MAX_LANES:
        raise Invalid(f'plan.json needs {MIN_LANES}-{MAX_LANES} lanes')
    names = [l.get('name') for l in lanes]
    if len(set(names)) != len(names) or not all(isinstance(n, str) and re.match(r'^[\w-]+$', n) for n in names):
        raise Invalid('lane names must be unique words (letters, digits, "_", "-")')
    for l in lanes:
        if l.get('side') not in SIDES:
            raise Invalid(f'lane {l["name"]}: "side" must be one of {sorted(SIDES)}')
        if not l.get('allow'):
            raise Invalid(f'lane {l["name"]}: "allow" needs at least one source pattern')
    if not {l['side'] for l in lanes} == set(SIDES):
        raise Invalid('a cross-check needs at least one "should" lane and one "is" lane')
    for i, a in enumerate(lanes):
        for b in lanes[i + 1:]:
            for pa in a['allow']:
                for pb in b['allow']:
                    if pa.startswith('query:') and pb.startswith('query:'):
                        continue  # query refs resolve inside each lane's own sources/<lane>/ folder
                    x, y = literal_prefix(pa), literal_prefix(pb)
                    if x.startswith(y) or y.startswith(x):
                        raise Invalid(f'lanes {a["name"]} and {b["name"]} may read the same sources ({pa!r} vs {pb!r}). '
                                      'Agreement on a shared source is not evidence: narrow the patterns so they are disjoint')
    return ids, {l['name']: l for l in lanes}


def allowed(lane, target):
    ok = any(fnmatch.fnmatchcase(target, p) for p in lane['allow'])
    return ok and not any(fnmatch.fnmatchcase(target, p) for p in lane.get('deny', []))


def classify_ref(ref, lane, cc_dir, repo):
    """Return a flag ('' when the ref is usable as cited, else why it counts as inference).
    Prefixed forms are tried before path:line, which would otherwise read `query:1` as path "query", line 1."""
    m = SRC_REF.match(ref)
    if m:
        if m['lane'] != lane['name'] or not allowed(lane, ref.split('#')[0]):
            return 'out-of-lane'
        return '' if os.path.isfile(os.path.join(cc_dir, 'sources', m['lane'], m['file'])) else 'unverifiable'
    m = QUERY_REF.match(ref)
    if m:
        if not allowed(lane, ref):
            return 'out-of-lane'
        return '' if os.path.isfile(os.path.join(cc_dir, 'sources', lane['name'], f'query-{m["id"]}.md')) else 'unverifiable'
    m = RUN_REF.match(ref)
    if m:
        if not allowed(lane, ref):
            return 'out-of-lane'
        return '' if os.path.isfile(os.path.join(repo, m['path'])) else 'unverifiable'
    m = PATH_REF.match(ref)
    if m:
        if not allowed(lane, m['path']):
            return 'out-of-lane'
        full = os.path.join(repo, m['path'])
        if not os.path.isfile(full):
            return 'unverifiable'
        with open(full, encoding='utf-8', errors='replace') as f:
            count = sum(1 for _ in f)
        first, last = int(m['line']), int(m['end'] or m['line'])
        return '' if 1 <= first <= last <= count else 'unverifiable'
    return 'unverifiable'


def read_lane(path, lane, plan_ids, cc_dir, repo):
    data = load(path, f'lane file for {lane["name"]}')
    if data.get('lane') != lane['name'] or not isinstance(data.get('items'), list):
        raise Invalid(f'{path}: needs {{"lane": "{lane["name"]}", "items": [...]}}')
    out = {}
    for it in data['items']:
        iid = str(it.get('id'))
        if iid not in plan_ids:
            raise Invalid(f'{path}: item {iid!r} is not in plan.json')
        sources = []
        for s in it.get('sources') or []:
            t = s.get('type')
            if t not in TYPES:
                raise Invalid(f'{path}: item {iid}: type {t!r} must be one of {sorted(TYPES)}')
            if t not in SIDES[lane['side']]:
                raise Invalid(f'{path}: item {iid}: a "{lane["side"]}" lane cannot cite {t!r} '
                              f'(allowed: {sorted(SIDES[lane["side"]])}). Relabel it or move the source to the right lane')
            ref = s.get('ref') or ''
            flag = classify_ref(ref, lane, cc_dir, repo) if t != 'inference' else ''
            sources.append({'ref': ref, 'type': 'inference' if flag else t, 'flag': flag, 'lane': lane['name']})
        if not sources:
            sources.append({'ref': '', 'type': 'inference', 'flag': '', 'lane': lane['name']})
        out[iid] = {'claim': it.get('claim', ''), 'sources': sources}
    return out


def read_compare(path, covered):
    data = load(path, 'compare.json')
    rows = {str(r.get('id')): r for r in data.get('items') or []}
    for iid in covered:
        r = rows.get(iid)
        if not r or r.get('status') not in STATUSES:
            raise Invalid(f'{path}: item {iid} needs a status in {STATUSES}')
        if r['status'] != 'match' and not r.get('question'):
            raise Invalid(f'{path}: item {iid} is {r["status"]} and needs a yes/no "question"')
    return rows


def final_status(compare_status, types):
    """The invariants: intent evidence is required to proceed; current state alone is never a rule."""
    if not types & INTENT:
        return 'current-state' if 'observed' in types else 'question'
    return 'proceed' if compare_status == 'match' else compare_status


def check_answers(cc_dir):
    path = os.path.join(cc_dir, 'answers.json')
    if not os.path.exists(path):
        return []
    rows = load(path, 'answers.json')
    for i, r in enumerate(rows if isinstance(rows, list) else [None]):
        if not isinstance(r, dict) or not r.get('item') or not r.get('verbatim') or 'interpretation' not in r:
            raise Invalid(f'answers.json row {i}: needs "item", "verbatim" (the human\'s exact words) and '
                          '"interpretation" (yours, may be ""); only the verbatim text counts as a decision')
    return rows


def run(cc_dir, repo):
    plan = load(os.path.join(cc_dir, 'plan.json'), 'plan.json')
    ids, lanes = check_plan(plan)
    try:
        max_rounds = int(plan.get('max_rounds') or DEFAULT_MAX_ROUNDS)
    except (TypeError, ValueError):
        raise Invalid('plan.json "max_rounds" must be a whole number (default 3)')
    rounds = sorted(int(m[1]) for d in os.listdir(cc_dir) if (m := ROUND_DIR.match(d)))
    if not rounds or rounds != list(range(1, rounds[-1] + 1)):
        raise Invalid('need round-1/ .. round-<n>/ with no gaps')
    state, mismatch_by_round = {}, []
    for n in rounds:
        rdir = os.path.join(cc_dir, f'round-{n}')
        lane_data = {name: read_lane(os.path.join(rdir, f'lane-{name}.json'), lane, ids, cc_dir, repo)
                     for name, lane in lanes.items()}
        covered = sorted({i for d in lane_data.values() for i in d}, key=ids.index)
        if n == 1 and covered != ids:
            raise Invalid(f'round-1 lanes must cover every item; missing {sorted(set(ids) - set(covered))}')
        compare = read_compare(os.path.join(rdir, 'compare.json'), covered)
        for iid in covered:
            earlier = state[iid]['sources'] if iid in state else []  # later rounds add evidence, never drop it
            sources = earlier + [s for d in lane_data.values() if iid in d for s in d[iid]['sources']]
            types = {s['type'] for s in sources}
            r = compare[iid]
            state[iid] = {'status': final_status(r['status'], types), 'types': types,
                          'sources': sources, 'should': r.get('should', ''), 'is': r.get('is', ''),
                          'question': r.get('question') or f'Is this behavior intended? {r.get("is", "")}'.strip(),
                          'round': n}
        mismatch_by_round.append({i for i in covered if state[i]['status'] == 'mismatch'})
    answers = check_answers(cc_dir)
    n = rounds[-1]
    deepen = [i for i in ids if state[i]['status'] in ('insufficient', 'question')]
    new_mismatch = mismatch_by_round[-1] - set().union(*mismatch_by_round[:-1]) if n > 1 else mismatch_by_round[-1]
    if not deepen:
        stop = 'yes (nothing left that more evidence could settle)'
    elif n > 1 and not new_mismatch:
        stop = f'yes (round {n} found no new mismatch)'
    elif n >= max_rounds:
        stop = f'yes (max rounds {max_rounds})'
    else:
        stop = f'no ({len(deepen)} items to deepen in round {n + 1}: {", ".join(deepen)})'
    render(cc_dir, plan, ids, state, answers)
    return state, stop


def cell(text):
    return str(text).replace('|', '\\|').replace('\n', ' ')


def refs(sources, side_lanes):
    picked = [s for s in sources if s['lane'] in side_lanes]
    return '; '.join(f'{s["ref"] or "(none)"} [{s["type"]}{", " + s["flag"] if s["flag"] else ""}]' for s in picked) or '(none)'


def render(cc_dir, plan, ids, state, answers):
    text = {str(i['id']): i.get('text', '') for i in plan['items']}
    should = {l['name'] for l in plan['lanes'] if l['side'] == 'should'}
    is_ = {l['name'] for l in plan['lanes'] if l['side'] == 'is'}
    res = ['# Cross-check results', '', '| Item | Status | Evidence types | Should be (source) | Is (source) | Flags |',
           '|---|---|---|---|---|---|']
    q = ['# Questions for the human', '', 'Answer yes/no. Answers go to answers.json verbatim, with your reading kept apart.', '']
    nr = ['# Not turned into rules', '', 'Backed only by current state. They describe what is, not what should be.', '',
          '| Item | Current-state description | Source |', '|---|---|---|']
    for i in ids:
        s = state[i]
        flags = sorted({x['flag'] for x in s['sources'] if x['flag']})
        res.append(f'| {cell(i)} {cell(text[i])} | {s["status"]} | {", ".join(sorted(s["types"]))} | '
                   f'{cell(s["should"])} ({cell(refs(s["sources"], should))}) | {cell(s["is"])} ({cell(refs(s["sources"], is_))}) | '
                   f'{", ".join(flags)} |')
        if s['status'] != 'proceed':
            q += [f'- **{i}.** {s["question"]}', f'  - Should be: {s["should"] or "(no intent evidence)"} — {refs(s["sources"], should)}',
                  f'  - Is: {s["is"] or "(nothing observed)"} — {refs(s["sources"], is_)}']
        if s['status'] == 'current-state':
            nr.append(f'| {cell(i)} | {cell(s["is"] or text[i])} | {cell(refs(s["sources"], is_))} |')
    if answers:
        q += ['', '## Answers so far', '', '| Item | Verbatim | Interpretation |', '|---|---|---|']
        q += [f'| {cell(a.get("item", ""))} | {cell(a["verbatim"])} | {cell(a["interpretation"])} |' for a in answers]
    for name, lines in (('results.md', res), ('questions.md', q), ('not-rules.md', nr)):
        with open(os.path.join(cc_dir, name), 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')


def main(argv=None):
    p = argparse.ArgumentParser(description='Check a devkit cross-check run and render results')
    p.add_argument('command', choices=['check'])
    p.add_argument('cc_dir')
    p.add_argument('--repo', default='.', help='repo root that path:line refs are relative to')
    a = p.parse_args(argv)
    try:
        state, stop = run(os.path.abspath(a.cc_dir), os.path.abspath(a.repo))
    except Invalid as e:
        print(f'cross_check: {e}', file=sys.stderr)
        return 1
    counts = {}
    for s in state.values():
        counts[s['status']] = counts.get(s['status'], 0) + 1
    print('items: ' + ', '.join(f'{k} {v}' for k, v in sorted(counts.items())))
    print(f'wrote results.md, questions.md, not-rules.md in {a.cc_dir}')
    print(f'STOP: {stop}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
