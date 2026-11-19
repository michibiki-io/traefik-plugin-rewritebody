"""Publish a tagged source release from a merged pull request's own commits."""

import json
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory


TAG = re.compile(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")
SUBJECT = re.compile(r"^([a-z]+)(?:\([^()\n]+\))?(!)?: .+")
BREAKING = re.compile(r"^BREAKING[ -]CHANGES?: ", re.MULTILINE)


def output(*argv):
    return subprocess.check_output(argv, text=True).strip()


def version_for(messages, previous):
    bump = 0
    for message in messages:
        subject = SUBJECT.fullmatch(message.split("\n", 1)[0])
        if BREAKING.search(message) or (subject and subject[2]):
            return (previous[0] + 1, 0, 0) if previous else (0, 1, 0)
        if subject and subject[1] == "feat":
            bump = 2
        elif subject and subject[1] in {"fix", "perf", "revert"}:
            bump = max(bump, 1)
    if not bump:
        return None
    if previous is None:
        return (0, 1, 0)
    major, minor, patch = previous
    return (major, minor + 1, 0) if bump == 2 else (major, minor, patch + 1)


def versions_from(*options):
    return {
        tuple(map(int, match.groups()))
        for tag in output("git", "tag", "--list", *options).splitlines()
        if (match := TAG.fullmatch(tag))
    }


def format_tag(version):
    return "v" + ".".join(map(str, version))


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    pr_number = int(os.environ["PR_NUMBER"])
    merge_commit = os.environ["MERGE_COMMIT"]
    if not re.fullmatch(r"[0-9a-f]{40}", merge_commit):
        raise SystemExit("The merged PR must provide a full commit SHA.")
    subprocess.run(["git", "merge-base", "--is-ancestor", merge_commit, "HEAD"], check=True)

    existing = versions_from("--points-at", merge_commit)
    if len(existing) > 1:
        raise SystemExit("Multiple release tags already point to the merge commit.")
    tag = format_tag(next(iter(existing))) if existing else None
    if tag is not None:
        if subprocess.run(["gh", "release", "view", tag, "--repo", repo],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            print(f"Release {tag} already exists.")
            return

    pages = json.loads(output("gh", "api", "--paginate", "--slurp",
                              f"repos/{repo}/pulls/{pr_number}/commits?per_page=100"))
    commits = [commit for page in pages for commit in page]
    if len(commits) != int(os.environ["PR_COMMIT_COUNT"]):
        raise SystemExit("GitHub did not return the complete PR commit history.")
    messages = [commit["commit"]["message"] for commit in commits]
    if tag is None:
        previous = max(versions_from("--merged", merge_commit), default=None)
        version = version_for(messages, previous)
        if version is None:
            print("No releasable commit in the merged pull request.")
            return
        if version in versions_from():
            raise SystemExit(f"Release tag {format_tag(version)} already exists on another commit.")
        tag = format_tag(version)
        subprocess.run([
            "git", "-c", "user.name=github-actions[bot]",
            "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
            "tag", "--annotate", tag, "--message", f"Release {tag}", merge_commit,
        ], check=True)
        subprocess.run(["git", "push", "origin", f"refs/tags/{tag}"], check=True)

    notes = [f"Merged pull request: https://github.com/{repo}/pull/{pr_number}", "## Commits"]
    for commit, message in zip(commits, messages, strict=True):
        subject, _, body = message.partition("\n")
        notes.append(f"- {subject} (`{commit['sha'][:12]}`)")
        notes.extend(f"  {line}" for line in body.strip().splitlines())
    with TemporaryDirectory() as directory:
        path = Path(directory, "notes.md")
        path.write_text("\n\n".join(notes[:2]) + "\n\n" + "\n".join(notes[2:]) + "\n",
                        encoding="utf-8")
        subprocess.run([
            "gh", "release", "create", tag, "--repo", repo, "--verify-tag",
            "--title", tag, "--notes-file", str(path),
        ], check=True)


if __name__ == "__main__":
    main()
