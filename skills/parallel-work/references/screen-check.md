# Screen check without run-app

Read only in step 4-5 when the repo has no `.devkit/runtime.json` and the user starts the server.

- Tell the user where to start it and to stop any server already on the same port first. Don't check against a server started from another path: find the listener's folder (orca: `orca ports --json`; macOS/Linux: `lsof -nP -iTCP:<port> -sTCP:LISTEN -t`, then `lsof -a -p <pid> -d cwd -Fn`; Windows: `Get-NetTCPConnection -LocalPort <port> -State Listen` → `Get-Process -Id <OwningProcess>`); ask the user if it is still unclear. Confirm the browser actually receives the new code.
