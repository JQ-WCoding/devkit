# Recheck and failure handling

Read the step 1-1 section when step 1's output has an "Open findings" section; read "On failure" when the fetch fails or the recorded SHA is gone.

## 1-1. Recheck open findings

For each open finding, read the current code at its `file` on the remote branch (`git show origin/<branch>:<path>`) and decide whether it still holds. "File changed since" only says where to look; it does not mean fixed.

| Result | Action |
|---|---|
| Fixed | Report as fixed with the fixing commit; close in step 6 |
| Still holds | Carry it into this report and that developer's message as "not yet addressed" |
| User judges it not a problem | Close with `--reason withdrawn` in step 6 |

## On failure

- Fetch fails: ask the user to check remote access, and whether to review the locally known remote branch with `--no-fetch`.
- The recorded SHA is not in the remote history (force update etc.): the script falls back to the last N days and says so; mention it in the report.
