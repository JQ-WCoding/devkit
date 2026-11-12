# Workspace: in-place (no git)

Every worker edits the same folder, `<repo>`. There are no branches, commits or merges, and no history to roll back to.

## Step 1 additions

- Combine or order tasks if any file could overlap: the edits happen at the same time in the same folder and can't be separated afterwards.
- **Ordered tasks**: launch the later task after the earlier worker reports.
- **Screen check location**: `<repo>`.
- Approval table adds: there is no rollback history · whether to back up the folder first.

## Step 2: prepare

Record the folder's state before launching (add `--backup` if a backup was approved):

```bash
python3 -I <scripts>/inplace_snapshot.py snapshot <repo> <scratchpad>/inplace [--backup]
```

- It skips VCS, dependency and cache folders (`.git`, `node_modules`, `.venv`, `__pycache__`, …). Build output folders (`build`, `dist`, `target`) are not skipped by default, since in a plain folder they may hold sources; add them with `--exclude <folder name>` when they are only output.
- The work folder for every task is `<repo>`.

## Step 3: check actual results

```bash
python3 -I <scripts>/inplace_snapshot.py changed <repo> <scratchpad>/inplace
```

It lists added, modified and deleted files. Compare the list with each report's file list, and report any file that no report mentions or that two tasks both changed.

## Step 4

- Skip 4-1 to 4-3.
- 4-4 scope is the `changed` list; run the checks in `<repo>`.
- Restore files from `<scratchpad>/inplace/backup/` only on user request, and only the files they name.
- 4-7: keep `<scratchpad>/inplace/` until the user says to delete it.
