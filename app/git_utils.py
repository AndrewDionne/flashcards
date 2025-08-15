import os
import shutil
import time
from pathlib import Path
from git import Repo
from git.exc import GitCommandError

LOCK_FILE = Path(".git/index.lock")
PUSH_LOCK = Path(".push_in_progress")

def commit_and_push_changes(message: str):
    """Commit and push changes to GitHub with lock handling."""
    repo = Repo(".")

    # 1. If another push is still in progress, wait up to 30 seconds then skip
    if PUSH_LOCK.exists():
        print("⏳ Another push is already in progress. Waiting...")
        waited = 0
        while PUSH_LOCK.exists() and waited < 30:
            time.sleep(2)
            waited += 2
        if PUSH_LOCK.exists():
            print("⚠️ Push skipped because another process is still running.")
            return

    # 2. Create push lock to mark push in progress
    PUSH_LOCK.touch()

    try:
        # 3. Clean up stale Git lock if it exists
        if LOCK_FILE.exists():
            print("⚠️ Removing stale Git lock file...")
            LOCK_FILE.unlink()

        repo.git.add(all=True)
        if repo.is_dirty(untracked_files=True):
            repo.index.commit(message)
            origin = repo.remote(name="origin")
            origin.push()
            print("✅ Changes committed and pushed.")
        else:
            print("ℹ️ No changes to commit.")

    except GitCommandError as e:
        print(f"❌ Git error: {e}")
    finally:
        # 4. Always remove the push lock
        if PUSH_LOCK.exists():
            PUSH_LOCK.unlink()

def delete_multiple_sets_and_push(set_names):
    repo_path = os.getcwd()
    deleted_paths = []

    for set_name in set_names:
        paths = [
            os.path.join(repo_path, "docs", "output", set_name),
            os.path.join(repo_path, "docs", "static", set_name),
            os.path.join(repo_path, "docs", "sets", set_name)
        ]
        for path in paths:
            if os.path.exists(path):
                shutil.rmtree(path)
                deleted_paths.append(path)
                print(f"🧹 Deleted: {path}")
            else:
                print(f"⚠️ Not found: {path}")

    if deleted_paths:
        commit_and_push_changes(f"🗑️ Deleted sets: {', '.join(set_names)}")
    else:
        print("ℹ️ No files to delete.")

def delete_set_and_push(set_name):
    repo_path = os.getcwd()
    paths = [
        os.path.join(repo_path, "docs", "output", set_name),
        os.path.join(repo_path, "docs", "static", set_name),
        os.path.join(repo_path, "docs", "sets", set_name)
    ]

    for path in paths:
        if os.path.exists(path):
            shutil.rmtree(path)
            print(f"🧹 Deleted: {path}")
        else:
            print(f"⚠️ Not found: {path}")

    commit_and_push_changes(f"🗑️ Deleted flashcard set: {set_name}")
