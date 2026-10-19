# Git Guide — publishing this dataset

Everything below is run **by you**, from the repository folder. The agent will not commit or push anything.

Repository folder:

```
C:\Users\AARUSH\OneDrive\Desktop\Tech\VIBE CODING\OpenCode Projects\VIBE_DATASET
```

Remote:

```
https://github.com/codec07/programDataset.git
```

---

## 0. Before you start: two warnings

**OneDrive.** This folder is inside OneDrive. OneDrive syncs files while Git is reading them, and it also syncs `.git/` — which can corrupt the repository or create `file.conflict` copies. Pick one:

- *Recommended:* pause OneDrive sync while you work (`right-click tray icon → Pause syncing → 2 hours`), or
- move the project outside OneDrive, e.g. `C:\Dev\programDataset`, and work there.

Either way, do not run `git` and a big OneDrive upload at the same time.

**Secrets.** Do not commit API keys, tokens, `.env` files, or personal paths. This repo's `.gitignore` already covers the common artifacts, but check `git status` before every commit.

---

## 1. Verify the remote exists and is empty

```powershell
git ls-remote https://github.com/codec07/programDataset.git
```

- No output → the repo is empty. Perfect, continue.
- You see `refs/heads/main` or `refs/heads/master` → it already has commits. Skip to **Step 4 (existing repo)** below.
- `Repository not found` → check the URL, that the repo exists, and that you're authenticated.

---

## 2. Initialize locally

```powershell
cd "C:\Users\AARUSH\OneDrive\Desktop\Tech\VIBE CODING\OpenCode Projects\VIBE_DATASET"

git init -b main
```

`-b main` avoids the old `master` default and the later "unrelated histories" confusion.

> **Note:** this folder already contains an empty `.git` (branch `main`, no commits, no remote). Running `git init -b main` again is safe — it prints `Reinitialized existing Git repository` and changes nothing. You can confirm with `git log` (should say the branch has no commits) and `git remote -v` (should print nothing) before continuing.

Set your identity once per machine (skip if already set):

```powershell
git config --global user.name "codec07"
git config --global user.email "you@example.com"
```

Recommended for Windows, avoids line-ending churn:

```powershell
git config --global core.autocrlf true
```

---

## 3. Review what will be committed

```powershell
git status
```

Expected: `README.md`, `DATASET_CARD.md`, `CONTRIBUTING.md`, `LICENSE`, `.gitignore`, `tools/`, `Python/`.

If you see `__pycache__`, `.db`, `.log`, `.wav`, or `.png` files, stop — fix `.gitignore` first. Then confirm nothing is already staged:

```powershell
git status --short
```

Stage everything:

```powershell
git add .
git status --short
```

Sanity-check the size and file count before committing:

```powershell
git ls-files | Measure-Object -Line
git ls-files | ForEach-Object { (Get-Item $_).Length } | Measure-Object -Sum
```

A few hundred small text files should be well under 10 MB.

---

## 4. First commit

```powershell
git commit -m "feat: add Python program dataset (5 domains, 100+ single-file programs)"
```

If Git complains about `user.name` / `user.email`, set them from Step 2.

---

## 5. Connect and push

### 5a. Empty remote (normal first-time case)

```powershell
git remote add origin https://github.com/codec07/programDataset.git
git remote -v
git push -u origin main
```

`-u` links your local `main` to `origin/main`, so later you can just run `git push`.

When prompted:
- **Username:** `codec07`
- **Password:** a **Personal Access Token**, not your GitHub password.

Create one at: GitHub → Settings → Developer settings → Personal access tokens → **Fine-grained tokens** → Repository access: *Only select repositories* → `programDataset` → Permissions: **Contents: Read and write** → Generate → copy it.

Git Credential Manager (bundled with Git for Windows) will offer a browser sign-in instead — that works too and is easier.

### 5b. Remote already has commits

```powershell
git remote add origin https://github.com/codec07/programDataset.git
git fetch origin
git branch --set-upstream-to=origin/main main
git pull --rebase origin main      # put your commit on top
git push -u origin main
```

If the remote's default branch is `master`, replace `main` with `master` in the commands above, or run
`git branch -M main` locally and change the default branch in GitHub → Settings → Branches.

### 5c. If `git remote add` says "remote origin already exists"

```powershell
git remote set-url origin https://github.com/codec07/programDataset.git
```

---

## 6. Verify the push

```powershell
git log --oneline -1
git status
```

`git status` should say `Your branch is up to date with 'origin/main'.` and `nothing to commit, working tree clean`.

Then open <https://github.com/codec07/programDataset> and confirm the file tree looks right.

---

## 7. Normal workflow from now on

```powershell
git status                      # what changed
git diff                        # review unstaged edits
git add Python/algorithms/trie.py
git commit -m "feat(python/algorithms): add trie with prefix search"
git push
```

Commit messages used in this repo:

```
feat(python/<domain>): add <program>
fix(python/<domain>): <what was broken>
docs: update Python index / dataset card
chore: regenerate manifest
```

One logical change per commit. Don't mix a new program with a repo-wide reformat.

---

## 8. Regenerating the manifest before you push

If `tools/build_manifest.py` exists and you've added programs:

```powershell
python tools/build_manifest.py
git add manifest.json
git commit -m "chore: regenerate dataset manifest"
```

---

## 9. Common problems

| Symptom | Cause | Fix |
|---|---|---|
| `fatal: not a git repository` | wrong folder | `cd` into the folder containing `.git`, check with `Get-ChildItem -Force` |
| `remote origin already exists` | remote already added | `git remote set-url origin <url>` |
| `Updates were rejected because the remote contains work…` | remote has commits you don't | `git pull --rebase origin main`, then push |
| `refusing to merge unrelated histories` | local and remote were created separately | `git pull origin main --allow-unrelated-histories`, resolve, commit, push |
| `Authentication failed` | password used instead of token | use a PAT, or let Credential Manager sign you in |
| `LF will be replaced by CRLF` | Windows line endings | harmless warning; keep `core.autocrlf true` |
| Push hangs or fails midway | OneDrive sync / network | pause OneDrive, retry `git push` |
| `Filename too long` | deep paths on Windows | `git config --system core.longpaths true` (admin shell) |
| Accidentally staged a secret | — | `git restore --staged <file>`, rotate the secret if it was ever pushed |

---

## 10. Undo cheat-sheet (before pushing)

```powershell
git restore --staged <file>        # unstage, keep changes
git restore <file>                 # discard working changes (destructive)
git commit --amend -m "new msg"    # fix the last commit message
git reset --soft HEAD~1            # undo last commit, keep changes staged
```

After pushing, prefer new commits over rewriting history. If you must rewrite a branch you already pushed:

```powershell
git push --force-with-lease
```

Never use plain `--force` on a shared branch.

---

## 11. What "done" looks like

```powershell
git status
# On branch main
# Your branch is up to date with 'origin/main'.
# nothing to commit, working tree clean

git ls-files | Measure-Object -Line
# a few hundred files

git log --oneline -3
# chore: regenerate dataset manifest
# feat: add Python program dataset ...
```

Then share the repo URL. The README and `DATASET_CARD.md` are what people read first — keep them accurate as the dataset grows.
