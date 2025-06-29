# version_control/vcs.py
import os
import json
import shutil
import hashlib
from typing import Dict, List, Optional

class Repository:
    def __init__(self, path: str):
        self.path = path
        self.repo_dir = os.path.join(path, '.vcs')
        self.staging_area = os.path.join(self.repo_dir, 'staging')
        self.commits_dir = os.path.join(self.repo_dir, 'commits')
        self.branches_dir = os.path.join(self.repo_dir, 'branches')
        self.ignore_file = os.path.join(self.repo_dir, 'ignore')
        
        # Initialise repository structure
        os.makedirs(self.staging_area, exist_ok=True)
        os.makedirs(self.commits_dir, exist_ok=True)
        os.makedirs(self.branches_dir, exist_ok=True)
        
        # Create initial branch
        with open(os.path.join(self.branches_dir, 'main'), 'w') as f:
            f.write('0')  # Initial commit hash
        
        # Create ignore file if not exists
        if not os.path.exists(self.ignore_file):
            with open(self.ignore_file, 'w') as f:
                f.write('.vcs\n')

    def add(self, filepath: str):
        """Stage a file for commit"""
        # Check if file should be ignored
        if self._should_ignore(filepath):
            print(f"Skipping {filepath}: file is ignored")
            return
        
        # Create staging area copy
        filename = os.path.basename(filepath)
        dest = os.path.join(self.staging_area, filename)
        shutil.copy2(filepath, dest)

    def commit(self, message: str) -> str:
        """Create a commit with staged files"""
        # Generate commit hash
        commit_hash = self._generate_commit_hash()
        commit_path = os.path.join(self.commits_dir, commit_hash)
        os.makedirs(commit_path)
        
        # Move staged files to commit directory
        for filename in os.listdir(self.staging_area):
            src = os.path.join(self.staging_area, filename)
            dest = os.path.join(commit_path, filename)
            shutil.move(src, dest)
        
        # Save commit metadata
        metadata = {
            'message': message,
            'timestamp': os.path.getctime(commit_path),
            'files': os.listdir(commit_path)
        }
        with open(os.path.join(commit_path, 'metadata.json'), 'w') as f:
            json.dump(metadata, f)
        
        # Update current branch
        current_branch_path = os.path.join(self.branches_dir, 'main')
        with open(current_branch_path, 'w') as f:
            f.write(commit_hash)
        
        return commit_hash

    def log(self) -> List[Dict]:
        """View commit history"""
        commits = []
        for commit_hash in sorted(os.listdir(self.commits_dir)):
            commit_path = os.path.join(self.commits_dir, commit_hash)
            metadata_path = os.path.join(commit_path, 'metadata.json')
            
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            commits.append({
                'hash': commit_hash,
                'message': metadata['message'],
                'timestamp': metadata['timestamp'],
                'files': metadata['files']
            })
        
        return commits

    def branch(self, name: str):
        """Create a new branch"""
        # Get current branch's latest commit
        current_branch_path = os.path.join(self.branches_dir, 'main')
        with open(current_branch_path, 'r') as f:
            latest_commit = f.read().strip()
        
        # Create branch file with current commit
        branch_path = os.path.join(self.branches_dir, name)
        with open(branch_path, 'w') as f:
            f.write(latest_commit)

    def diff(self, branch1: str, branch2: str) -> Dict:
        """Compare files between two branches"""
        # Get latest commits for each branch
        branch1_path = os.path.join(self.branches_dir, branch1)
        branch2_path = os.path.join(self.branches_dir, branch2)
        
        with open(branch1_path, 'r') as f:
            commit1 = f.read().strip()
        
        with open(branch2_path, 'r') as f:
            commit2 = f.read().strip()
        
        # Compare files in commits
        commit1_path = os.path.join(self.commits_dir, commit1)
        commit2_path = os.path.join(self.commits_dir, commit2)
        
        diff_result = {
            'added': [],
            'removed': [],
            'modified': []
        }
        
        commit1_files = set(os.listdir(commit1_path) if os.path.exists(commit1_path) else [])
        commit2_files = set(os.listdir(commit2_path) if os.path.exists(commit2_path) else [])
        
        diff_result['added'] = list(commit2_files - commit1_files)
        diff_result['removed'] = list(commit1_files - commit2_files)
        
        # Simple modification check (content comparison)
        for common_file in commit1_files.intersection(commit2_files):
            file1_path = os.path.join(commit1_path, common_file)
            file2_path = os.path.join(commit2_path, common_file)
            
            with open(file1_path, 'r') as f1, open(file2_path, 'r') as f2:
                if f1.read() != f2.read():
                    diff_result['modified'].append(common_file)
        
        return diff_result

    def clone(self, destination: str):
        """Clone the entire repository"""
        shutil.copytree(self.path, destination)

    def _generate_commit_hash(self) -> str:
        """Generate a unique commit hash"""
        staging_contents = [f for f in os.listdir(self.staging_area)]
        hash_input = json.dumps(sorted(staging_contents)).encode()
        return hashlib.sha256(hash_input).hexdigest()[:8]

    def _should_ignore(self, filepath: str) -> bool:
        """Check if a file should be ignored"""
        filename = os.path.basename(filepath)
        
        with open(self.ignore_file, 'r') as f:
            ignore_patterns = [line.strip() for line in f.readlines()]
        
        return any(
            pattern in filepath or 
            pattern == filename or 
            filename.endswith(pattern.replace('*', ''))
            for pattern in ignore_patterns
        )

def init_repo(path: str) -> Repository:
    """Initialize a new repository"""
    return Repository(path)