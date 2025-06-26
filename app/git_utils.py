import os
import shutil
from git import Repo

def commit_and_push_changes(message="Update"):
    repo = Repo(os.getcwd())
    if repo.is_dirty(untracked_files=True):
        repo.git.add(all=True)
        repo.index.commit(message)
        repo.remote(name="origin").push()

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
