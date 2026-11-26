"""Build the workspace's git history with only the task's starting state.

The fixed twin of vulnerable_leaky: a fresh repository with a single commit, and no copy
of the reference solution anywhere in the image.
"""

import os
import pathlib
import subprocess

ws = pathlib.Path(os.environ["HACKFLOOR_WORKSPACE"])
GIT = ["git", "-c", "user.name=task", "-c", "user.email=task@example.invalid", "-c", "commit.gpgsign=false"]


def git(*args):
    subprocess.run([*GIT, *args], cwd=ws, check=True, capture_output=True)


git("init", "-q", "-b", "main")
git("add", "-A")
git("commit", "-q", "-m", "Task starting state")
