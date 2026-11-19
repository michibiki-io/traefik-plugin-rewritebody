"""Publish source releases for merged PRs in main's first-parent history."""

import json
import os
import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from time import sleep


WORKFLOW = ".github/workflows/release.yml"
TAG = re.compile(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")
SUBJECT = re.compile(r"^([a-z]+)(?:\([^()\n]+\))?(!)?: .+", re.IGNORECASE)
BREAKING = re.compile(r"^BREAKING[ -]CHANGES?: ", re.MULTILINE)
COMMITS_QUERY = """
query($owner: String!, $name: String!, $number: Int!, $endCursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      commits(first: 100, after: $endCursor) {
        totalCount
        nodes { commit { oid message } }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}
"""


def output(*argv):
    return subprocess.check_output(argv, text=True).strip()


def version_for(messages, previous):
    bump = 0
    for message in messages:
        subject = SUBJECT.fullmatch(message.split("\n", 1)[0])
        if BREAKING.search(message) or (subject and subject[2]):
            return (previous[0] + 1, 0, 0) if previous else (0, 1, 0)
        if subject and subject[1].lower() == "feat":
            bump = 2
        elif subject and subject[1].lower() in {"fix", "perf", "revert"}:
            bump = max(bump, 1)
    if not bump:
        return None
    if previous is None:
        return (0, 1, 0)
    major, minor, patch = previous
    return (major, minor + 1, 0) if bump == 2 else (major, minor, patch + 1)


def format_tag(version):
    return "v" + ".".join(map(str, version))


def release_tags():
    return {
        tuple(map(int, match.groups())): output("git", "rev-list", "-n", "1", f"refs/tags/{tag}")
        for tag in output("git", "tag", "--list", "v*").splitlines()
        if (match := TAG.fullmatch(tag))
    }


def merged_pr(repo, commit_sha):
    pages = json.loads(output("gh", "api", "--paginate", "--slurp",
                              f"repos/{repo}/commits/{commit_sha}/pulls?per_page=100"))
    matches = [
        pr["number"]
        for page in pages for pr in page
        if pr["merged_at"] and pr["merge_commit_sha"] == commit_sha
        and pr["base"]["ref"] == "main" and pr["base"]["repo"]["full_name"] == repo
    ]
    if len(matches) > 1:
        raise SystemExit(f"Multiple merged PRs match {commit_sha}.")
    return matches[0] if matches else None


def pr_commits(repo, number):
    owner, name = repo.split("/")
    pages = json.loads(output("gh", "api", "graphql", "--paginate", "--slurp",
                              "-f", f"query={COMMITS_QUERY}", "-f", f"owner={owner}",
                              "-f", f"name={name}", "-F", f"number={number}"))
    results = [page["data"]["repository"]["pullRequest"]["commits"] for page in pages]
    commits = [node["commit"] for result in results for node in result["nodes"]]
    if not results or len(commits) != results[-1]["totalCount"]:
        raise SystemExit(f"GitHub did not return the complete history of PR #{number}.")
    return commits


def release_exists(repo, tag):
    return subprocess.run(["gh", "release", "view", tag, "--repo", repo],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def publish(repo, number, commit_sha, commits, version, tags):
    tag = format_tag(version)
    # Go's module proxy requires a /vN path when publishing major releases from v2.
    modfile = output("git", "show", f"{commit_sha}:go.mod")
    module = re.search(r"^module\s+(\S+)", modfile, re.MULTILINE)
    if not module or (version[0] >= 2 and not module[1].endswith(f"/v{version[0]}")):
        raise SystemExit(f"The Go module path does not support tag {tag}.")
    if version in tags and tags[version] != commit_sha:
        raise SystemExit(f"Release tag {tag} already exists on another commit.")
    if version not in tags:
        subprocess.run([
            "git", "-c", "user.name=github-actions[bot]",
            "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
            "tag", "--annotate", tag, "--message", f"Release {tag}", commit_sha,
        ], check=True)
        subprocess.run(["git", "push", "origin", f"refs/tags/{tag}"], check=True)
        tags[version] = commit_sha

    notes = [f"Merged pull request: https://github.com/{repo}/pull/{number}", "", "## Commits", ""]
    for commit in commits:
        subject, _, body = commit["message"].partition("\n")
        notes.append(f"- {subject} (`{commit['oid'][:12]}`)")
        notes.extend(f"  {line}" for line in body.strip().splitlines())
    with TemporaryDirectory() as directory:
        path = Path(directory, "notes.md")
        path.write_text("\n".join(notes) + "\n", encoding="utf-8")
        subprocess.run([
            "gh", "release", "create", tag, "--repo", repo, "--verify-tag",
            "--title", tag, "--notes-file", str(path),
        ], check=True)


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    history = output("git", "rev-list", "--first-parent", "--reverse", "HEAD").splitlines()
    trigger = os.environ["GITHUB_SHA"]
    if trigger not in history:
        raise SystemExit("The triggering commit is missing from main's first-parent history.")
    # The push can arrive before GitHub indexes the updated PR association.
    for delay in (0, 2, 4, 8):
        sleep(delay)
        trigger_pr = merged_pr(repo, trigger)
        if trigger_pr is not None:
            break
    if trigger_pr is None:
        print("The push does not identify a PR merged into main.")
        return

    tags = release_tags()
    positions = {sha: index for index, sha in enumerate(history)}
    previous = max((version for version, sha in tags.items() if sha in positions), default=None)
    through = positions[trigger]
    if previous is None:
        introduced = output("git", "log", "-1", "--first-parent", "--diff-filter=A",
                            "--format=%H", "HEAD", "--", WORKFLOW)
        after = positions[introduced]
    else:
        last_tag_sha = tags[previous]
        after = positions[last_tag_sha]
        if through < after:
            print("A later merge has already been released.")
            return
        # Recover when a prior job pushed its tag and then failed to create the Release.
        if not release_exists(repo, format_tag(previous)):
            number = merged_pr(repo, last_tag_sha)
            if number is None:
                raise SystemExit("The latest release tag has no merged PR.")
            publish(repo, number, last_tag_sha, pr_commits(repo, number), previous, tags)
        after += 1

    for commit_sha in history[after:through + 1]:
        number = trigger_pr if commit_sha == trigger else merged_pr(repo, commit_sha)
        if number is None:
            continue
        commits = pr_commits(repo, number)
        version = version_for([commit["message"] for commit in commits], previous)
        if version is None:
            print(f"No releasable commit in PR #{number}.")
            continue
        publish(repo, number, commit_sha, commits, version, tags)
        previous = version


if __name__ == "__main__":
    main()
