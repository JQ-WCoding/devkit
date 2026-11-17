"""cross_check.py tests against throwaway cross-check folders. One test per invariant.
Usage: python3 -I skills/analyze/scripts/cross_check_test.py
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, 'cross_check.py')
PY = sys.executable
FAILS = []


def check(name, cond, out=''):
    print(('ok    ' if cond else 'FAIL  ') + name)
    if not cond:
        FAILS.append(name)
        print('      ' + out.replace('\n', '\n      ')[:1500])


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(data if isinstance(data, str) else json.dumps(data))


LANES = [{'name': 'intent', 'side': 'should', 'allow': ['docs/spec/**', 'src:intent/*']},
         {'name': 'code', 'side': 'is', 'allow': ['src/**', 'query:*']}]


def setup(items=('1',), lanes=LANES, max_rounds=3):
    """A repo with docs/spec/policy.md (10 lines) and src/app.py (10 lines), and an empty cross-check dir."""
    repo = tempfile.mkdtemp(prefix='cc-')
    write(os.path.join(repo, 'docs', 'spec', 'policy.md'), 'policy\n' * 10)
    write(os.path.join(repo, 'src', 'app.py'), 'code\n' * 10)
    cc = os.path.join(repo, '.devkit', 'work', 'T-1', 'cross-check')
    write(os.path.join(cc, 'plan.json'), {'items': [{'id': i, 'text': f'item {i}'} for i in items],
                                          'lanes': lanes, 'max_rounds': max_rounds})
    return repo, cc


def lane(cc, n, name, items):
    write(os.path.join(cc, f'round-{n}', f'lane-{name}.json'), {'lane': name, 'items': items})


def compare(cc, n, rows):
    write(os.path.join(cc, f'round-{n}', 'compare.json'), {'items': rows})


def run(repo, cc):
    r = subprocess.run([PY, '-I', SCRIPT, 'check', cc, '--repo', repo], capture_output=True, text=True, timeout=60)
    return r.returncode, r.stdout + r.stderr


def read(cc, name):
    with open(os.path.join(cc, name), encoding='utf-8') as f:
        return f.read()


def test_code_only_draft_is_not_rules():
    ids = [str(i) for i in range(1, 17)]
    repo, cc = setup(ids)
    lane(cc, 1, 'intent', [{'id': i, 'claim': 'no record found', 'sources': []} for i in ids])
    lane(cc, 1, 'code', [{'id': i, 'claim': 'code does it', 'sources': [{'ref': 'src/app.py:3', 'type': 'observed'}]} for i in ids])
    compare(cc, 1, [{'id': i, 'status': 'match', 'is': 'code does it', 'question': ''} for i in ids])
    code, out = run(repo, cc)
    nr = read(cc, 'not-rules.md')
    check('16-line draft backed only by code: 16 not-rules rows, nothing proceeds',
          code == 0 and 'current-state 16' in out and 'proceed' not in out and len(re.findall(r'^\| \d+ \|', nr, re.M)) == 16, out + nr)


def test_match_without_intent_is_overridden():
    repo, cc = setup()
    lane(cc, 1, 'intent', [{'id': '1', 'claim': 'guess', 'sources': [{'ref': '', 'type': 'inference'}]}])
    lane(cc, 1, 'code', [{'id': '1', 'claim': 'x', 'sources': [{'ref': '', 'type': 'inference'}]}])
    compare(cc, 1, [{'id': '1', 'status': 'match'}])
    code, out = run(repo, cc)
    check('comparator "match" with inference only becomes a question', code == 0 and 'question 1' in out, out)


def test_match_with_intent_proceeds():
    repo, cc = setup()
    lane(cc, 1, 'intent', [{'id': '1', 'claim': 'policy says x', 'sources': [{'ref': 'docs/spec/policy.md:2', 'type': 'decision'}]}])
    lane(cc, 1, 'code', [{'id': '1', 'claim': 'code does x', 'sources': [{'ref': 'src/app.py:2', 'type': 'observed'}]}])
    compare(cc, 1, [{'id': '1', 'status': 'match', 'should': 'x', 'is': 'x'}])
    code, out = run(repo, cc)
    check('match backed by a decision proceeds and stops the loop',
          code == 0 and 'proceed 1' in out and out.strip().endswith('STOP: yes (nothing left that more evidence could settle)'), out)


def test_is_lane_cannot_cite_decision():
    repo, cc = setup()
    lane(cc, 1, 'intent', [{'id': '1', 'claim': 'x', 'sources': []}])
    lane(cc, 1, 'code', [{'id': '1', 'claim': 'x', 'sources': [{'ref': 'src/app.py:2', 'type': 'decision'}]}])
    compare(cc, 1, [{'id': '1', 'status': 'match'}])
    code, out = run(repo, cc)
    check('a ref labelled decision in an "is" lane is rejected', code == 1 and 'cannot cite' in out, out)


def test_should_lane_cannot_cite_observed():
    repo, cc = setup()
    lane(cc, 1, 'intent', [{'id': '1', 'claim': 'x', 'sources': [{'ref': 'docs/spec/policy.md:1', 'type': 'observed'}]}])
    lane(cc, 1, 'code', [{'id': '1', 'claim': 'x', 'sources': []}])
    compare(cc, 1, [{'id': '1', 'status': 'match'}])
    code, out = run(repo, cc)
    check('a ref labelled observed in a "should" lane is rejected', code == 1 and 'cannot cite' in out, out)


def test_out_of_lane_and_unverifiable_refs_count_as_inference():
    repo, cc = setup(('1', '2', '3'))
    lane(cc, 1, 'intent', [
        {'id': '1', 'claim': 'cites code', 'sources': [{'ref': 'src/app.py:1', 'type': 'decision'}]},
        {'id': '2', 'claim': 'vague', 'sources': [{'ref': 'the wiki somewhere', 'type': 'agreement'}]},
        {'id': '3', 'claim': 'past end', 'sources': [{'ref': 'docs/spec/policy.md:99', 'type': 'decision'}]}])
    lane(cc, 1, 'code', [{'id': i, 'claim': 'x', 'sources': [{'ref': 'src/app.py:1', 'type': 'observed'}]} for i in '123'])
    compare(cc, 1, [{'id': i, 'status': 'match'} for i in '123'])
    code, out = run(repo, cc)
    res = read(cc, 'results.md')
    check('out-of-lane, unclassifiable and missing-line refs downgrade to inference (current state only)',
          code == 0 and 'current-state 3' in out and 'out-of-lane' in res and 'unverifiable' in res, out + res)


def test_src_and_query_refs():
    repo, cc = setup()
    write(os.path.join(cc, 'sources', 'intent', 'ticket-12.md'), 'origin: https://tracker/12\nthe rule\n')
    write(os.path.join(cc, 'sources', 'code', 'query-q1.md'), 'select 1;\n1\n')
    lane(cc, 1, 'intent', [{'id': '1', 'claim': 'owner says', 'sources': [{'ref': 'src:intent/ticket-12.md#c3', 'type': 'decision'}]}])
    lane(cc, 1, 'code', [{'id': '1', 'claim': 'data shows', 'sources': [{'ref': 'query:q1', 'type': 'observed'}]}])
    compare(cc, 1, [{'id': '1', 'status': 'mismatch', 'question': 'Is the data wrong?'}])
    code, out = run(repo, cc)
    q = read(cc, 'questions.md')
    check('exported src: and query: refs are accepted; a mismatch becomes a question with both sides',
          code == 0 and 'mismatch 1' in out and 'src:intent/ticket-12.md#c3 [decision]' in q and 'query:q1 [observed]' in q, out + q)


def test_overlapping_lanes_are_an_error():
    lanes = [{'name': 'intent', 'side': 'should', 'allow': ['docs/**']},
             {'name': 'code', 'side': 'is', 'allow': ['docs/rules/**']}]
    repo, cc = setup(lanes=lanes)
    code, out = run(repo, cc)
    check('lane patterns that can read the same files are an error', code == 1 and 'same sources' in out, out)


def test_needs_both_sides():
    lanes = [{'name': 'a', 'side': 'is', 'allow': ['src/**']}, {'name': 'b', 'side': 'is', 'allow': ['db/**']}]
    repo, cc = setup(lanes=lanes)
    code, out = run(repo, cc)
    check('a plan without a "should" lane is refused', code == 1 and 'should' in out, out)


def test_missing_status_and_question():
    repo, cc = setup()
    lane(cc, 1, 'intent', [{'id': '1', 'claim': 'x', 'sources': []}])
    lane(cc, 1, 'code', [{'id': '1', 'claim': 'x', 'sources': []}])
    compare(cc, 1, [{'id': '1', 'status': 'insufficient'}])
    code, out = run(repo, cc)
    check('insufficient without a yes/no question is refused', code == 1 and 'question' in out, out)


def two_rounds(round2_status):
    repo, cc = setup(('1', '2'))
    lane(cc, 1, 'intent', [{'id': '1', 'claim': 'x', 'sources': [{'ref': 'docs/spec/policy.md:1', 'type': 'decision'}]},
                           {'id': '2', 'claim': '?', 'sources': []}])
    lane(cc, 1, 'code', [{'id': i, 'claim': 'x', 'sources': [{'ref': 'src/app.py:1', 'type': 'observed'}]} for i in '12'])
    compare(cc, 1, [{'id': '1', 'status': 'mismatch', 'question': 'Q1?'}, {'id': '2', 'status': 'insufficient', 'question': 'Q2?'}])
    lane(cc, 2, 'intent', [{'id': '2', 'claim': 'found it', 'sources': [{'ref': 'docs/spec/policy.md:5', 'type': 'decision'}]}])
    lane(cc, 2, 'code', [{'id': '2', 'claim': 'x', 'sources': [{'ref': 'src/app.py:5', 'type': 'observed'}]}])
    compare(cc, 2, [{'id': '2', 'status': round2_status, 'question': 'Q2 again?'}])
    return repo, cc


def test_round_without_new_mismatch_stops():
    repo, cc = two_rounds('insufficient')
    code, out = run(repo, cc)
    check('round 2 with no new mismatch stops', code == 0 and 'STOP: yes (round 2 found no new mismatch)' in out, out)


def test_round_one_continues_on_open_items():
    repo, cc = setup(('1',))
    lane(cc, 1, 'intent', [{'id': '1', 'claim': '?', 'sources': []}])
    lane(cc, 1, 'code', [{'id': '1', 'claim': '?', 'sources': []}])
    compare(cc, 1, [{'id': '1', 'status': 'insufficient', 'question': 'Q?'}])
    code, out = run(repo, cc)
    check('round 1 with an item to deepen continues', code == 0 and 'STOP: no (1 items to deepen in round 2: 1)' in out, out)


def test_max_rounds_stops():
    repo, cc = setup(('1',), max_rounds=1)
    lane(cc, 1, 'intent', [{'id': '1', 'claim': '?', 'sources': []}])
    lane(cc, 1, 'code', [{'id': '1', 'claim': '?', 'sources': []}])
    compare(cc, 1, [{'id': '1', 'status': 'insufficient', 'question': 'Q?'}])
    code, out = run(repo, cc)
    check('reaching max rounds stops', code == 0 and 'STOP: yes (max rounds 1)' in out, out)


def test_round_one_must_cover_every_item():
    repo, cc = setup(('1', '2'))
    lane(cc, 1, 'intent', [{'id': '1', 'claim': 'x', 'sources': []}])
    lane(cc, 1, 'code', [{'id': '1', 'claim': 'x', 'sources': []}])
    compare(cc, 1, [{'id': '1', 'status': 'insufficient', 'question': 'Q?'}])
    code, out = run(repo, cc)
    check('round 1 that skips an item is refused', code == 1 and 'cover every item' in out, out)


def test_answers_keep_verbatim_apart():
    repo, cc = setup()
    lane(cc, 1, 'intent', [{'id': '1', 'claim': 'x', 'sources': []}])
    lane(cc, 1, 'code', [{'id': '1', 'claim': 'x', 'sources': []}])
    compare(cc, 1, [{'id': '1', 'status': 'insufficient', 'question': 'One-way only?'}])
    write(os.path.join(cc, 'answers.json'), [{'item': '1', 'interpretation': 'confirmed one-way'}])
    code, out = run(repo, cc)
    check('an answer without the verbatim wording is refused', code == 1 and 'verbatim' in out, out)
    write(os.path.join(cc, 'answers.json'), [{'item': '1', 'verbatim': 'probably, for now', 'interpretation': 'one-way for now'}])
    code, out = run(repo, cc)
    q = read(cc, 'questions.md')
    check('answers render with verbatim and interpretation in separate columns',
          code == 0 and '| 1 | probably, for now | one-way for now |' in q, out + q)


def test_numeric_query_id_and_int_item_ids():
    repo, cc = setup()
    plan = json.load(open(os.path.join(cc, 'plan.json')))
    plan['items'] = [{'id': 1, 'text': 'item 1'}]
    plan['max_rounds'] = None
    write(os.path.join(cc, 'plan.json'), plan)
    write(os.path.join(cc, 'sources', 'code', 'query-1.md'), 'select 1;\n1\n')
    lane(cc, 1, 'intent', [{'id': 1, 'claim': 'x', 'sources': [{'ref': 'docs/spec/policy.md:1', 'type': 'decision'}]}])
    lane(cc, 1, 'code', [{'id': 1, 'claim': 'x', 'sources': [{'ref': 'query:1', 'type': 'observed'}]}])
    compare(cc, 1, [{'id': 1, 'status': 'match'}])
    code, out = run(repo, cc)
    res = read(cc, 'results.md') if code == 0 else ''
    check('query:1 is a query ref, integer ids and max_rounds null work',
          code == 0 and 'proceed 1' in out and 'query:1 [observed]' in res, out + res)


def test_query_lanes_do_not_overlap():
    lanes = [{'name': 'intent', 'side': 'should', 'allow': ['docs/spec/**']},
             {'name': 'sql', 'side': 'is', 'allow': ['src/**', 'query:*']},
             {'name': 'dash', 'side': 'is', 'allow': ['dash/**', 'query:*']}]
    repo, cc = setup(lanes=lanes)
    lane(cc, 1, 'intent', [{'id': '1', 'claim': 'x', 'sources': []}])
    lane(cc, 1, 'sql', [{'id': '1', 'claim': 'x', 'sources': []}])
    lane(cc, 1, 'dash', [{'id': '1', 'claim': 'x', 'sources': []}])
    compare(cc, 1, [{'id': '1', 'status': 'insufficient', 'question': 'Q?'}])
    code, out = run(repo, cc)
    check('two lanes may both allow query:* (each reads its own sources folder)', code == 0, out)


def test_line_zero_and_range_end_are_checked():
    repo, cc = setup(('1', '2', '3'))
    lane(cc, 1, 'intent', [{'id': i, 'claim': 'x', 'sources': [{'ref': 'docs/spec/policy.md:1', 'type': 'decision'}]} for i in '123'])
    lane(cc, 1, 'code', [{'id': '1', 'claim': 'x', 'sources': [{'ref': 'src/app.py:0', 'type': 'observed'}]},
                         {'id': '2', 'claim': 'x', 'sources': [{'ref': 'src/app.py:5-9999', 'type': 'observed'}]},
                         {'id': '3', 'claim': 'x', 'sources': [{'ref': 'src/app.py:5-10', 'type': 'observed'}]}])
    compare(cc, 1, [{'id': i, 'status': 'match'} for i in '123'])
    code, out = run(repo, cc)
    res = read(cc, 'results.md')
    check('line 0 and a range past the end are unverifiable; a range inside the file is fine',
          code == 0 and 'src/app.py:0 [inference, unverifiable]' in res
          and 'src/app.py:5-9999 [inference, unverifiable]' in res and 'src/app.py:5-10 [observed]' in res, out + res)


def test_later_rounds_keep_earlier_evidence():
    repo, cc = setup(('1',))
    lane(cc, 1, 'intent', [{'id': '1', 'claim': 'policy', 'sources': [{'ref': 'docs/spec/policy.md:2', 'type': 'decision'}]}])
    lane(cc, 1, 'code', [{'id': '1', 'claim': 'no record found', 'sources': []}])
    compare(cc, 1, [{'id': '1', 'status': 'insufficient', 'question': 'Q?'}])
    lane(cc, 2, 'intent', [{'id': '1', 'claim': 'nothing new', 'sources': []}])
    lane(cc, 2, 'code', [{'id': '1', 'claim': 'code', 'sources': [{'ref': 'src/app.py:2', 'type': 'observed'}]}])
    compare(cc, 2, [{'id': '1', 'status': 'match'}])
    code, out = run(repo, cc)
    check('round 1 decision still counts after round 2 finds only code', code == 0 and 'proceed 1' in out, out)


def test_invalid_lane_json():
    repo, cc = setup()
    write(os.path.join(cc, 'round-1', 'lane-intent.json'), 'Here is my answer: {')
    lane(cc, 1, 'code', [{'id': '1', 'claim': 'x', 'sources': []}])
    compare(cc, 1, [{'id': '1', 'status': 'match'}])
    code, out = run(repo, cc)
    check('a lane reply that is not JSON is refused with the next action', code == 1 and 'verbatim' in out, out)


if __name__ == '__main__':
    for fn in [v for k, v in sorted(globals().items()) if k.startswith('test_')]:
        fn()
    print(f'\n{"FAILED: " + ", ".join(FAILS) if FAILS else "all passed"}')
    sys.exit(1 if FAILS else 0)
