"""
GitHub Pages automatic publisher for podcast files.
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("github_publisher")


class GitHubPublisher:
    """Automatically publish podcast files to GitHub Pages."""
    
    def __init__(self, repo_path: Path, branch: str = "main"):
        """
        Initialize GitHub publisher.
        
        Args:
            repo_path: Path to git repository
            branch: Git branch to push to (default: main)
        """
        self.repo_path = Path(repo_path)
        self.branch = branch
        
    def _run_git_command(self, command: list[str]) -> tuple[bool, str]:
        """
        Run a git command and return success status and output.
        
        Args:
            command: Git command as list of strings
            
        Returns:
            Tuple of (success: bool, output: str)
        """
        try:
            result = subprocess.run(
                command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            success = result.returncode == 0
            output = result.stdout if success else result.stderr
            return success, output
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)
    
    def check_git_status(self) -> bool:
        """
        Check if repository has changes to commit.
        
        Returns:
            True if there are changes, False otherwise
        """
        success, output = self._run_git_command(["git", "status", "--porcelain"])
        if success:
            return len(output.strip()) > 0
        return False
    
    def add_files(self, patterns: list[str] = None) -> bool:
        """
        Add files to git staging area.
        
        Args:
            patterns: List of file patterns to add (default: ["podcast/"])
            
        Returns:
            True if successful
        """
        if patterns is None:
            patterns = ["podcast/"]
        
        for pattern in patterns:
            success, output = self._run_git_command(["git", "add", pattern])
            if not success:
                logger.error(f"Failed to add {pattern}: {output}")
                return False
        
        logger.info(f"Added files: {', '.join(patterns)}")
        return True
    
    def commit(self, message: str, author: Optional[str] = None) -> bool:
        """
        Create a git commit.
        
        Args:
            message: Commit message
            author: Optional author string (e.g., "Name <email>")
            
        Returns:
            True if successful
        """
        command = ["git", "commit", "-m", message]
        
        if author:
            command.extend(["--author", author])
        
        success, output = self._run_git_command(command)
        
        if success:
            logger.info(f"Commit created: {message}")
            return True
        else:
            # Check if there were no changes
            if "nothing to commit" in output.lower():
                logger.info("No changes to commit")
                return True
            logger.error(f"Commit failed: {output}")
            return False
    
    def push(self, force: bool = False) -> bool:
        """
        Push commits to remote repository.
        
        Args:
            force: Whether to force push (default: False)
            
        Returns:
            True if successful
        """
        command = ["git", "push", "origin", self.branch]
        
        if force:
            command.append("--force")
        
        # Set upstream on first push
        command.extend(["-u"])
        
        success, output = self._run_git_command(command)
        
        if success:
            logger.info(f"Pushed to origin/{self.branch}")
            return True
        else:
            # If already up-to-date
            if "up-to-date" in output.lower() or "already up to date" in output.lower():
                logger.info("Repository already up-to-date")
                return True
            logger.error(f"Push failed: {output}")
            return False
    
    def publish(self, episode_title: str, patterns: list[str] = None) -> bool:
        """
        Full publish cycle: add, commit, push.
        
        Args:
            episode_title: Title of the episode for commit message
            patterns: File patterns to add (default: ["podcast/"])
            
        Returns:
            True if successful
        """
        logger.info(f"Starting publish for: {episode_title}")
        
        # Check if there are changes
        if not self.check_git_status():
            logger.info("No changes to publish")
            return True
        
        # Add files
        if not self.add_files(patterns):
            return False
        
        # Commit
        commit_message = f"Add podcast episode: {episode_title}"
        if not self.commit(commit_message):
            return False
        
        # Push
        if not self.push():
            return False
        
        logger.info(f"Successfully published: {episode_title}")
        return True
    
    def get_pages_url(self, repo_owner: str, repo_name: str) -> str:
        """
        Get GitHub Pages URL for the repository.
        
        Args:
            repo_owner: GitHub username
            repo_name: Repository name
            
        Returns:
            GitHub Pages URL
        """
        return f"https://{repo_owner}.github.io/{repo_name}"


def publish_episode(
    repo_path: Path,
    episode_title: str,
    patterns: list[str] = None
) -> bool:
    """
    Convenience function to publish an episode.
    
    Args:
        repo_path: Path to repository
        episode_title: Episode title
        patterns: File patterns to add
        
    Returns:
        True if successful
    """
    publisher = GitHubPublisher(repo_path)
    return publisher.publish(episode_title, patterns)
