#!/usr/bin/env python3
"""
Docker Compose Project Organizer

This script finds all Docker Compose projects using the Docker Compose CLI,
organizes them into a structured format, and copies them to a target directory
for GitHub or other version control systems.

Each compose project gets its own directory with:
- compose.yml (renamed from the original docker-compose.yml)
- .env file (if found) or .env.example (as a template)
"""

import os
import sys
import shutil
import argparse
import subprocess
import json
import tempfile
from pathlib import Path


def find_compose_projects_via_cli():
    """
    Find all Docker Compose projects using the Docker Compose CLI.
    
    Returns:
        list: Found compose files with their paths
    """
    compose_files = []
    
    try:
        # First, try with 'docker compose ls --format json' (newer Docker versions)
        result = subprocess.run(
            ['docker', 'compose', 'ls', '--format', 'json', '--all'],
            capture_output=True, text=True, check=True
        )
        
        if result.stdout.strip():
            projects = json.loads(result.stdout)
            
            for project in projects:
                project_name = project.get('Name')
                config_files = project.get('ConfigFiles')
                
                if not project_name or not config_files:
                    continue
                
                # Config files might be a comma-separated string or a list
                if isinstance(config_files, str):
                    config_files = config_files.split(',')
                
                for config_file in config_files:
                    config_file = config_file.strip()
                    if config_file:
                        # Check if this file is in a Docker volume (like Portainer managed ones)
                        is_in_volume = config_file.startswith('/data/compose/')
                        
                        # For files in Docker volumes, we'll handle them differently
                        parent_dir = os.path.dirname(os.path.abspath(config_file))
                        env_path = os.path.join(parent_dir, '.env')
                        env_exists = os.path.exists(env_path) if not is_in_volume else False
                        
                        compose_files.append({
                            'compose_path': config_file,
                            'env_path': env_path if env_exists else None,
                            'project_name': project_name,
                            'parent_dir': parent_dir,
                            'is_in_volume': is_in_volume
                        })
    
    except (subprocess.SubprocessError, json.JSONDecodeError) as e:
        print(f"Warning: Could not retrieve Docker Compose projects via CLI: {e}")
        print("Falling back to filesystem search...")
    
    # If no projects were found via CLI, we'll fall back to filesystem search
    if not compose_files:
        print("No Docker Compose projects found via Docker CLI. Using filesystem search instead.")
        compose_files = find_compose_files_in_filesystem(['/home', '/opt', '/etc', '/var'])
    
    return compose_files


def extract_compose_from_volume(compose_path, project_name):
    """
    Extract a Docker Compose file from a Docker volume by using 'docker compose config'.
    This is used for files that are in Docker volumes and not directly accessible.
    
    Args:
        compose_path (str): Path to the compose file in the volume
        project_name (str): Name of the Docker Compose project
        
    Returns:
        str: Path to a temporary file containing the extracted compose content
    """
    try:
        # Use docker compose config to get the full configuration
        result = subprocess.run(
            ['docker', 'compose', '-p', project_name, 'config'],
            capture_output=True, text=True, check=True
        )
        
        # Create a temporary file for the config
        fd, temp_path = tempfile.mkstemp(suffix='.yml', prefix=f'compose_{project_name}_')
        with os.fdopen(fd, 'w') as f:
            f.write(result.stdout)
        
        print(f"Extracted compose config for {project_name} to temporary file: {temp_path}")
        return temp_path
        
    except subprocess.SubprocessError as e:
        print(f"Warning: Failed to extract compose config for {project_name}: {e}")
        return None


def find_compose_files_in_filesystem(search_dirs, exclude_dirs=None):
    """
    Find all Docker Compose files in the given directories.
    This is a fallback method if the Docker Compose CLI method fails.
    
    Args:
        search_dirs (list): Directories to search for compose files
        exclude_dirs (list): Directories to exclude from the search
        
    Returns:
        list: Found compose files with their paths
    """
    if exclude_dirs is None:
        exclude_dirs = []
    
    # Convert exclude_dirs to absolute paths
    exclude_dirs = [os.path.abspath(d) for d in exclude_dirs]
    
    compose_files = []
    compose_filenames = ['docker-compose.yml', 'docker-compose.yaml', 
                         'compose.yml', 'compose.yaml']
    
    for search_dir in search_dirs:
        search_path = Path(os.path.expanduser(search_dir))
        if not search_path.exists():
            print(f"Warning: Search path {search_path} does not exist. Skipping.")
            continue
            
        for root, dirs, files in os.walk(search_path):
            # Skip excluded directories
            root_path = Path(root).absolute()
            if any(str(root_path).startswith(ex) for ex in exclude_dirs):
                dirs[:] = []  # Don't traverse into subdirectories
                continue
                
            # Check for compose files
            for filename in files:
                if filename.lower() in compose_filenames:
                    compose_path = os.path.join(root, filename)
                    env_path = os.path.join(root, '.env')
                    env_exists = os.path.exists(env_path)
                    
                    compose_files.append({
                        'compose_path': compose_path,
                        'env_path': env_path if env_exists else None,
                        'project_name': Path(root).name,
                        'parent_dir': root,
                        'is_in_volume': False
                    })
    
    return compose_files


def create_project_structure(compose_files, target_dir, create_env_examples=True):
    """
    Create the project structure in the target directory.
    
    Args:
        compose_files (list): List of compose files found
        target_dir (str): Target directory to create the structure in
        create_env_examples (bool): Whether to create example .env files
        
    Returns:
        list: List of created project directories
    """
    target_path = Path(os.path.expanduser(target_dir))
    target_path.mkdir(parents=True, exist_ok=True)
    
    created_projects = []
    temp_files = []  # Track temp files to clean up later
    
    for compose_file in compose_files:
        # Determine project name - use the Docker Compose project name if available
        project_name = compose_file['project_name']
        
        # Handle files in Docker volumes
        compose_path = compose_file['compose_path']
        if compose_file.get('is_in_volume', False):
            print(f"Project {project_name} uses a compose file in a Docker volume: {compose_path}")
            extracted_path = extract_compose_from_volume(compose_path, project_name)
            if extracted_path:
                compose_path = extracted_path
                temp_files.append(extracted_path)
            else:
                print(f"Skipping project {project_name} as its compose file couldn't be extracted.")
                continue
        
        # Handle duplicate project names by appending parent path hash if needed
        project_dir = target_path / project_name
        original_project_dir = project_dir
        counter = 1
        
        while project_dir.exists():
            # For files in volumes, we can't do a direct file comparison
            if not compose_file.get('is_in_volume', False):
                # Check if this is the same project or a duplicate name
                existing_compose = list(project_dir.glob('compose.y*ml'))
                if existing_compose and os.path.samefile(compose_path, existing_compose[0]):
                    print(f"Project {project_name} already exists and is the same. Skipping.")
                    break
            
            project_dir = original_project_dir.with_name(f"{project_name}_{counter}")
            counter += 1
        
        if project_dir.exists() and not compose_file.get('is_in_volume', False):
            continue
            
        # Create the project directory
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy the compose file as compose.yml
        dest_compose = project_dir / 'compose.yml'
        try:
            shutil.copy2(compose_path, dest_compose)
        except (FileNotFoundError, PermissionError) as e:
            print(f"Error copying compose file for {project_name}: {e}")
            print(f"Skipping project {project_name}.")
            # Remove the project directory if it was just created
            if project_dir.exists() and len(list(project_dir.iterdir())) == 0:
                project_dir.rmdir()
            continue
        
        # Copy .env file if it exists and is accessible, otherwise create an example
        if compose_file['env_path'] and not compose_file.get('is_in_volume', False):
            try:
                dest_env = project_dir / '.env'
                shutil.copy2(compose_file['env_path'], dest_env)
                
                # Also create a .env.example file
                dest_env_example = project_dir / '.env.example'
                create_env_example(compose_file['env_path'], dest_env_example)
            except (FileNotFoundError, PermissionError) as e:
                print(f"Error copying .env file for {project_name}: {e}")
                # Continue anyway, we'll create an empty example
        
        # Always create a .env.example if requested
        if create_env_examples:
            dest_env_example = project_dir / '.env.example'
            if not dest_env_example.exists():
                create_empty_env_example(compose_path, dest_env_example)
        
        # Create a README.md with basic information
        create_readme(project_dir, project_name, compose_file)
        
        created_projects.append({
            'name': project_name,
            'dir': str(project_dir),
            'source': compose_file['parent_dir'],
            'config_file': compose_file['compose_path'],
            'is_in_volume': compose_file.get('is_in_volume', False)
        })
        
        print(f"Created project structure for {project_name} in {project_dir}")
    
    # Clean up any temporary files
    for temp_file in temp_files:
        try:
            os.remove(temp_file)
        except Exception as e:
            print(f"Warning: Could not remove temporary file {temp_file}: {e}")
    
    return created_projects


def create_env_example(env_path, dest_path):
    """
    Create a .env.example file based on the actual .env file by preserving
    keys but masking sensitive values.
    """
    with open(env_path, 'r') as f:
        env_content = f.readlines()
    
    with open(dest_path, 'w') as f:
        for line in env_content:
            line = line.strip()
            if not line or line.startswith('#'):
                f.write(f"{line}\n")
            else:
                try:
                    key, value = line.split('=', 1)
                    # Mask the value if it seems sensitive
                    sensitive_terms = ['password', 'secret', 'key', 'token', 'api']
                    if any(term in key.lower() for term in sensitive_terms):
                        f.write(f"{key}=YOUR_{key.upper()}_HERE\n")
                    else:
                        f.write(f"{key}=example_value\n")
                except ValueError:
                    # Line doesn't contain '=', write as is
                    f.write(f"{line}\n")


def create_empty_env_example(compose_path, dest_path):
    """
    Parse the compose file to extract environment variables and create
    a .env.example file with placeholder values.
    """
    # This is a simplified implementation
    # A full implementation would parse the compose YAML to extract env vars
    with open(dest_path, 'w') as f:
        f.write("# Environment Variables for this Docker Compose project\n")
        f.write("# Replace these values with your actual configuration\n\n")
        f.write("# Examples:\n")
        f.write("# DB_PASSWORD=your_secure_password\n")
        f.write("# API_KEY=your_api_key\n")


def create_readme(project_dir, project_name, compose_file):
    """
    Create a README.md file with basic information about the project.
    """
    readme_path = project_dir / 'README.md'
    
    with open(readme_path, 'w') as f:
        f.write(f"# {project_name.replace('_', ' ').title()}\n\n")
        f.write("## Description\n\n")
        f.write(f"Docker Compose configuration for {project_name}.\n\n")
        
        if compose_file.get('is_in_volume', False):
            f.write("**Note:** This compose file was extracted from a Docker volume and may not include all original settings.\n\n")
        
        f.write("## Usage\n\n")
        f.write("```bash\n")
        f.write("# Copy .env.example to .env and edit with your configuration\n")
        f.write("cp .env.example .env\n")
        f.write("nano .env\n\n")
        f.write("# Start the containers\n")
        f.write("docker compose up -d\n")
        f.write("```\n\n")
        f.write("## Original Location\n\n")
        f.write(f"This configuration was originally located at: `{compose_file['compose_path']}`\n")


def main():
    parser = argparse.ArgumentParser(
        description="Organize Docker Compose projects for GitHub"
    )
    parser.add_argument(
        '-t', '--target-dir', 
        default='~/docker-compose-projects',
        help='Target directory to create the project structure in'
    )
    parser.add_argument(
        '--fallback-search-dirs', 
        nargs='+', 
        default=['/home', '/opt', '/etc', '/var'],
        help='Directories to search for Docker Compose files if CLI method fails'
    )
    parser.add_argument(
        '--fallback-exclude-dirs', 
        nargs='+', 
        default=[],
        help='Directories to exclude from the fallback search'
    )
    parser.add_argument(
        '--no-env-examples', 
        action='store_false', 
        dest='create_env_examples',
        help='Do not create .env.example files'
    )
    parser.add_argument(
        '--use-filesystem-only',
        action='store_true',
        help='Use only filesystem search, skip Docker CLI'
    )
    parser.add_argument(
        '--skip-volume-files',
        action='store_true',
        help='Skip compose files stored in Docker volumes'
    )
    
    args = parser.parse_args()
    
    if args.use_filesystem_only:
        print(f"Searching for Docker Compose files in: {', '.join(args.fallback_search_dirs)}")
        if args.fallback_exclude_dirs:
            print(f"Excluding directories: {', '.join(args.fallback_exclude_dirs)}")
        compose_files = find_compose_files_in_filesystem(args.fallback_search_dirs, args.fallback_exclude_dirs)
    else:
        print("Finding Docker Compose projects using Docker Compose CLI...")
        compose_files = find_compose_projects_via_cli()
        
        # Filter out volume files if requested
        if args.skip_volume_files:
            original_count = len(compose_files)
            compose_files = [f for f in compose_files if not f.get('is_in_volume', False)]
            skipped_count = original_count - len(compose_files)
            if skipped_count > 0:
                print(f"Skipped {skipped_count} compose files stored in Docker volumes.")
    
    print(f"Found {len(compose_files)} Docker Compose project(s)")
    
    if not compose_files:
        print("No Docker Compose files found. Exiting.")
        return
    
    created_projects = create_project_structure(
        compose_files, 
        args.target_dir,
        args.create_env_examples
    )
    
    print(f"\nCreated {len(created_projects)} project(s) in {os.path.expanduser(args.target_dir)}")
    
    # Create a summary file
    summary_path = Path(os.path.expanduser(args.target_dir)) / 'SUMMARY.md'
    with open(summary_path, 'w') as f:
        f.write("# Docker Compose Projects Summary\n\n")
        f.write("| Project | Source Location | Config File | In Volume | Target Directory |\n")
        f.write("|---------|-----------------|-------------|-----------|------------------|\n")
        
        for project in created_projects:
            volume_status = "Yes" if project.get('is_in_volume', False) else "No"
            f.write(f"| {project['name']} | {project['source']} | {project['config_file']} | {volume_status} | {project['dir']} |\n")
    
    print(f"Created summary file at {summary_path}")


if __name__ == "__main__":
    main()
