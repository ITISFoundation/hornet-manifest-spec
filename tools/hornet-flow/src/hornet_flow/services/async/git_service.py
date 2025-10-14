"""Git operations service.

This module provides functionality for git repository operations including
cloning, version checking, and repository information extraction.
"""

import asyncio
import os
import subprocess
from pathlib import Path
from typing import Final

from ...model import Release

_GIT_TIMEOUT: Final[int] = 10
_GIT_VERSION_TIMEOUT: Final[int] = 5


async def _run_git_command_async(
    args: list[str], cwd: str | None = None, timeout: int = _GIT_TIMEOUT
) -> str:
    """Run git command asynchronously and return stdout.

    Raises:
        subprocess.CalledProcessError: If git command fails
        asyncio.TimeoutError: If command times out
    """
    assert args[0] == "git", "Only git commands are supported"

    process = await asyncio.create_subprocess_exec(
        *args, cwd=cwd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)

    if process.returncode != os.EX_OK:
        raise subprocess.CalledProcessError(
            process.returncode or os.EX_SOFTWARE, " ".join(args), stderr.decode()
        )

    return stdout.decode().strip()


async def _run_git_command_async_or_none(
    args: list[str], cwd: str | None = None, timeout: int = _GIT_VERSION_TIMEOUT
) -> str | None:
    """Try to run git command, return stdout or None if it fails.

    Raises:
        None: All exceptions are caught and return None
    """
    try:
        return await _run_git_command_async(args, cwd, timeout)
    except (subprocess.CalledProcessError, TimeoutError):
        return None


async def check_git_version_async() -> str | None:
    """Check if git is installed and return its version string (async version)."""
    return await _run_git_command_async_or_none(
        ["git", "--version"], timeout=_GIT_VERSION_TIMEOUT
    )


async def clone_repository(
    repo_url: str, commit_hash: str, target_dir: Path | str
) -> Path:
    """Clone repository and checkout specific commit (async version).

    Raises:
        ValueError: If repository URL is not HTTP(S)
        subprocess.CalledProcessError: If git commands fail
        asyncio.TimeoutError: If git commands timeout
    """
    if not repo_url.startswith("http://") and not repo_url.startswith("https://"):
        raise ValueError(f"Repository URL must be HTTP(S): {repo_url}")

    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)

    # Clone with depth 1 first
    await _run_git_command_async(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--no-single-branch",
            repo_url,
            str(target_path),
        ]
    )

    # Try to checkout the commit, if it fails, fetch it specifically
    try:
        await _run_git_command_async(
            ["git", "checkout", commit_hash], cwd=str(target_path)
        )
    except subprocess.CalledProcessError:
        # Commit not in shallow clone, fetch it specifically
        await _run_git_command_async(
            ["git", "fetch", "--depth", "1", "origin", commit_hash],
            cwd=str(target_path),
        )

        await _run_git_command_async(
            ["git", "checkout", commit_hash], cwd=str(target_path)
        )

    return target_path


async def extract_git_repo_info(repo_path: Path | str) -> Release:
    """Extract git repository information from a cloned repository (async version).

    Raises:
        ValueError: If repository path does not exist or git commands fail
        subprocess.CalledProcessError: If git commands fail
        asyncio.TimeoutError: If git commands timeout
    """
    repo_dir = Path(repo_path)

    if not repo_dir.exists():
        raise ValueError(f"Repository path does not exist: {repo_dir}")

    try:
        # Get the remote URL
        repo_url = await _run_git_command_async(
            ["git", "remote", "get-url", "origin"], cwd=str(repo_dir)
        )

        # Get current commit hash
        commit_hash = await _run_git_command_async(
            ["git", "rev-parse", "HEAD"], cwd=str(repo_dir)
        )

        # Get a human-readable label (try tag first, then branch, then short hash)
        label = commit_hash[:8]  # Default to short hash

        # Try to get tag
        tag = await _run_git_command_async_or_none(
            ["git", "describe", "--tags", "--exact-match", "HEAD"], cwd=str(repo_dir)
        )

        if tag:
            label = tag
        else:
            # Try to get branch name
            branch = await _run_git_command_async_or_none(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(repo_dir)
            )

            if branch and branch != "HEAD":  # Not in detached HEAD state
                label = branch

        return Release(
            origin="git",
            url=repo_url,
            label=label,
            marker=commit_hash,
        )

    except subprocess.CalledProcessError as e:
        msg = f"Failed to extract git repository information: {e}"
        raise ValueError(msg) from e
    except TimeoutError as e:
        msg = f"Git command timed out: {e}"
        raise ValueError(msg) from e
