import tempfile
import ast
import subprocess
import os
import shutil
from typing import Optional
from urllib.parse import urlparse

def is_safe_url(url: str) -> bool:
    """Basic sanitization for repository URLs."""
    try:
        parsed = urlparse(url)
        # Allow only github.com or similar trusted hosts for now
        return parsed.scheme in ["https", "git"] and "github.com" in parsed.netloc
    except Exception:
        return False

class RepoSandbox:
    """Context manager for a temporary git repository sandbox."""
    def __init__(self, repo_url: str):
        if not is_safe_url(repo_url):
            raise ValueError(f"Insecure or invalid repository URL: {repo_url}")
        self.repo_url = repo_url
        self.temp_dir = None
    
    def __enter__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="auditor_")
        print(f"Cloning {self.repo_url} into {self.temp_dir}...")
        
        try:
            # Clone with 1 depth for efficiency in forensic audit
            result = subprocess.run(
                ["git", "clone", "--depth", "1", self.repo_url, "."],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                check=True
            )
            return self.temp_dir
        except subprocess.CalledProcessError as e:
            # Cleanup on failure
            shutil.rmtree(self.temp_dir)
            raise RuntimeError(f"Git clone failed: {e.stderr}") from e
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print("Cleaned up git sandbox")

def extract_git_history(repo_path: str) -> str:
    """Extract commit history from the cloned repository."""
    try:
        result = subprocess.run(
            ["git", "log", "--pretty=format:%h - %an, %ar : %s"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error extracting git history: {e.stderr}"

def analyze_graph_structure(file_path: str) -> str:
    """Analyze Python file for LangGraph StateGraph usage using AST."""
    try:
        with open(file_path, "r") as f:
            tree = ast.parse(f.read())
        
        findings = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for StateGraph(...) calls
                if (isinstance(node.func, ast.Name) and node.func.id == 'StateGraph') or \
                   (isinstance(node.func, ast.Attribute) and node.func.attr == 'StateGraph'):
                    findings.append("Found StateGraph definition")
                
                # Check for .add_edge or .add_node
                if isinstance(node.func, ast.Attribute) and node.func.attr in ['add_edge', 'add_node']:
                    findings.append(f"Found {node.func.attr} call")
                    
        return f"AST Analysis: {', '.join(set(findings)) if findings else 'No graph structures found'}"
    except Exception as e:
        return f"AST parsing failed: {e}"
