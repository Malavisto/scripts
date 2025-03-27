
#!/usr/bin/env python3
"""
Docker Compose Project Organizer

This script finds all Docker Compose projects using the Docker Compose CLI,
organizes them into a structured format, and copies them to a target directory
for GitHub or other version control systems.

Each compose project gets its own directory with:
- compose.yml (renamed from the original docker-compose.yml)
- .env file (if found) or .env.example (as a template)
- Any override files (if present)
"""

import os
import sys
import shutil
import argparse
import subprocess
import json
import tempfile
from pathlib import Path
from collections import defaultdict


def find_compose_projects_via_cli():
    """
    Find all Docker Compose projects using the Docker Compose CLI.
    Groups files by project name to handle overrides properly.
    
    Returns:
        list: Found compose projects with their files
    """
    # Use a dictionary to group files by project name
    projects_dict = defaultdict(lambda: {
        'name': '',
        'config_files': [],
        'parent_dir': '',
        'is_in_volume': False
    })
    
    try:
        # Run 'docker compose ls --format json' (newer Docker versions)
        result = subprocess.run(
            ['docker', 'compose', 'ls', '--format', 'json', '--all'],
            capture_output=True, text=True, check=True
        )
        
        if result.stdout.strip():
            projects_data = json.loads(result.stdout)
            
            for project_data in projects_data:
                project_name = project_data.get('Name')
                config_files_str = project_data.get('ConfigFiles')
                
                if not project_name or not config_files_str:
                    continue
                
                # Config files might be a comma-separated string or a list
                config_files = config_files_str.split(',') if isinstance(config_files_str, str) else config_files_str
                
                # Get the parent directory from the first config file
                main_config = config_files[0].strip() if config_files else ""
                parent_dir = os.path.dirname(os.path.abspath(main_config)) if main_config else ""
                
                # Check if this is in a Docker volume
                is_in_volume = any(f.strip().startswith('/data/compose/') for f in config_files if f.strip())
                
                # Store the project information
                projects_dict[project_name] = {
                    'name': project_name,
                    'config_files': [f.strip() for f in config_files if f.strip()],
                    'parent_dir': parent_dir,
                    'is_in_volume': is_in_volume,
                    'env_path': os.path.join(parent_dir, '.env') if parent_dir and os.path.exists(os.path.join(parent_dir, '.env')) and not is_in_volume else None
                }
    
    except (subprocess.SubprocessError, json.JSONDecodeError) as e:
        print(f"Warning: Could not retrieve Docker Compose projects via CLI: {e}")
        print("Falling back to filesystem search...")
    
    # Convert the dictionary to a list
    projects_list = list(projects_dict.values())
    
    # If no projects were found via CLI, we'll fall back to filesystem search
    if not projects_list:
        print("No Docker Compose projects found via Docker CLI. Using filesystem search instead.")
        projects_list = find_compose_files_in_filesystem(['/home', '/opt', '/etc', '/var'])
    
    return projects_list


def extract_compose_from_volume(project_info):
    """
    Extract Docker Compose files from a Docker volume by using 'docker compose config'.
    This is used for projects that are in Docker volumes and not directly accessible.
    
    Args:
        project_info (dict): Project information including name and config files
        
    Returns:
        dict: Updated project information with extracted config paths or None if extraction failed
    """
    # Create a copy of the project info
    updated_info = project_info.copy()
    extracted_files = []
    temp_dir = None
    
    try:
        # Create a temporary directory for this project's files
        temp_dir = tempfile.mkdtemp(prefix=f'compose_{project_info["name"]}_')
        
        # Use docker compose config to get the full configuration
        cmd = ['docker', 'compose', '-p', project_info['name'], 'config']
        print(f"Executing command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True, 
            text=True
        )
        
        # Check if the command was successful
        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            print(f"Warning: Failed to extract compose config for {project_info['name']}: {error_msg}")
            print(f"Command exit code: {result.returncode}")
            print("This may happen if the compose file has errors or uses extensions not supported by 'docker compose config'")
            
            # Try with --no-interpolate flag (available in newer Docker Compose versions)
            print(f"Attempting to extract with --no-interpolate flag...")
            try:
                no_interpolate_result = subprocess.run(
                    ['docker', 'compose', '-p', project_info['name'], 'config', '--no-interpolate'],
                    capture_output=True, 
                    text=True,
                    check=True
                )
                # If this succeeds, use this output instead
                result = no_interpolate_result
                print(f"Extraction with --no-interpolate succeeded")
            except subprocess.SubprocessError as e:
                print(f"Extract with --no-interpolate also failed: {e}")
                # Clean up temp directory
                if temp_dir and os.path.exists(temp_dir):
                    try:
                        shutil.rmtree(temp_dir)
                    except Exception as cleanup_error:
                        print(f"Warning: Could not clean up temporary directory {temp_dir}: {cleanup_error}")
                return None
        
        # Save the main compose file
        main_config_path = os.path.join(temp_dir, 'compose.yml')
        with open(main_config_path, 'w') as f:
            f.write(result.stdout)
        
        extracted_files.append(main_config_path)
        
        # If there were multiple files, also save them individually with their original names
        for i, config_file in enumerate(project_info['config_files']):
            filename = os.path.basename(config_file)
            if filename.lower() in ('docker-compose.override.yml', 'docker-compose.override.yaml', 
                                   'compose.override.yml', 'compose.override.yaml'):
                override_path = os.path.join(temp_dir, 'compose.override.yml')
                
                # For override files, we can't get their content directly, but we'll create a placeholder
                with open(override_path, 'w') as f:
                    f.write(f"# This is a placeholder for the override file: {filename}\n")
                    f.write("# The actual content has been merged into the main compose.yml file\n")
                
                extracted_files.append(override_path)
        
        print(f"Extracted compose config for {project_info['name']} to temporary directory: {temp_dir}")
        
        # Update the project info
        updated_info['temp_dir'] = temp_dir
        updated_info['extracted_files'] = extracted_files
        updated_info['main_config'] = main_config_path
        
        return updated_info
        
    except subprocess.SubprocessError as e:
        print(f"Warning: Failed to extract compose config for {project_info['name']}: {e}")
        # Clean up temp directory if it was created
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as cleanup_error:
                print(f"Warning: Could not clean up temporary directory {temp_dir}: {cleanup_error}")
        return None


def find_compose_files_in_filesystem(search_dirs, exclude_dirs=None):
    """
    Find all Docker Compose files in the given directories.
    Groups files by parent directory to handle overrides properly.
    This is a fallback method if the Docker Compose CLI method fails.
    
    Args:
        search_dirs (list): Directories to search for compose files
        exclude_dirs (list): Directories to exclude from the search
        
    Returns:
        list: Found compose projects with their files
    """
    if exclude_dirs is None:
        exclude_dirs = []
    
    # Convert exclude_dirs to absolute paths
    exclude_dirs = [os.path.abspath(d) for d in exclude_dirs]
    
    # Use a dictionary to group files by directory
    projects_by_dir = defaultdict(lambda: {
        'config_files': [],
        'parent_dir': '',
        'is_in_volume': False
    })
    
    compose_filenames = ['docker-compose.yml', 'docker-compose.yaml', 
                         'compose.yml', 'compose.yaml',
                         'docker-compose.override.yml', 'docker-compose.override.yaml',
                         'compose.override.yml', 'compose.override.yaml']
    
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
            has_compose_file = False
            for filename in files:
                if filename.lower() in compose_filenames:
                    has_compose_file = True
                    compose_path = os.path.join(root, filename)
                    
                    # Add this file to the project
                    parent_dir = os.path.abspath(root)
                    projects_by_dir[parent_dir]['config_files'].append(compose_path)
                    projects_by_dir[parent_dir]['parent_dir'] = parent_dir
            
            # If this directory has compose files, check for .env file
            if has_compose_file:
                env_path = os.path.join(root, '.env')
                if os.path.exists(env_path):
                    projects_by_dir[os.path.abspath(root)]['env_path'] = env_path
    
    # Convert the directory-based dictionary to a list of projects
    projects_list = []
    for parent_dir, project_info in projects_by_dir.items():
        if not project_info['config_files']:
            continue
        
        # Use the directory name as the project name
        project_name = os.path.basename(parent_dir)
        
        # Sort config files - main files first, then overrides
        main_files = []
        override_files = []
        for config_file in project_info['config_files']:
            filename = os.path.basename(config_file).lower()
            if 'override' in filename:
                override_files.append(config_file)
            else:
                main_files.append(config_file)
        
        # Combine the sorted files
        sorted_config_files = main_files + override_files
        
        projects_list.append({
            'name': project_name,
            'config_files': sorted_config_files,
            'parent_dir': parent_dir,
            'is_in_volume': False,
            'env_path': project_info.get('env_path')
        })
    
    return projects_list


def create_project_structure(projects, target_dir, create_env_examples=True, handle_failed=True):
    """
    Create the project structure in the target directory.
    
    Args:
        projects (list): List of projects found
        target_dir (str): Target directory to create the structure in
        create_env_examples (bool): Whether to create example .env files
        handle_failed (bool): Whether to create placeholder structures for failed extractions
        
    Returns:
        list: List of created project directories
    """
    target_path = Path(os.path.expanduser(target_dir))
    target_path.mkdir(parents=True, exist_ok=True)
    
    created_projects = []
    failed_projects = []
    temp_dirs_to_clean = []  # Track temp directories to clean up later
    
    for project in projects:
        project_name = project['name']
        config_files = project['config_files']
        
        if not config_files:
            print(f"Warning: Project {project_name} has no config files. Skipping.")
            continue
        
        # Handle files in Docker volumes
        is_in_volume = project.get('is_in_volume', False)
        if is_in_volume:
            print(f"Project {project_name} uses compose files in a Docker volume")
            extracted_project = extract_compose_from_volume(project)
            if extracted_project:
                # Use the extracted files instead of the original ones
                config_files = extracted_project.get('extracted_files', [])
                if 'temp_dir' in extracted_project:
                    temp_dirs_to_clean.append(extracted_project['temp_dir'])
            else:
                print(f"Extraction failed for project {project_name}")
                if handle_failed:
                    print(f"Creating placeholder structure for manual configuration...")
                    placeholder_project = handle_failed_extraction(project, target_dir)
                    if placeholder_project:
                        failed_projects.append(placeholder_project)
                    continue
                else:
                    print(f"Skipping project {project_name} as its compose files couldn't be extracted.")
                    continue
        
        # Handle duplicate project names
        project_dir = target_path / project_name
        original_project_dir = project_dir
        counter = 1
        
        while project_dir.exists():
            # For files in volumes, we can't do a direct file comparison
            if not is_in_volume:
                # Check if this is the same project or a duplicate name
                existing_compose = list(project_dir.glob('compose.y*ml'))
                # Check the first config file if it exists
                if existing_compose and config_files and os.path.samefile(config_files[0], existing_compose[0]):
                    print(f"Project {project_name} already exists and is the same. Skipping.")
                    break
            
            project_dir = original_project_dir.with_name(f"{project_name}_{counter}")
            counter += 1
        
        if project_dir.exists() and not is_in_volume:
            continue
            
        # Create the project directory
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy/process the config files
        processed_files = []
        try:
            # The main compose file becomes compose.yml
            main_config = config_files[0] if config_files else None
            if main_config:
                dest_compose = project_dir / 'compose.yml'
                shutil.copy2(main_config, dest_compose)
                processed_files.append({
                    'source': main_config,
                    'dest': str(dest_compose),
                    'type': 'main'
                })
            
            # Any additional files (like overrides) are copied with their proper names
            for i, config_file in enumerate(config_files[1:], 1):
                filename = os.path.basename(config_file)
                # Standardize override filenames
                if 'override' in filename.lower():
                    dest_filename = 'compose.override.yml'
                else:
                    # Keep other filenames as is but standardize extension
                    base_name = os.path.splitext(filename)[0]
                    dest_filename = f"{base_name}.yml"
                
                dest_file = project_dir / dest_filename
                shutil.copy2(config_file, dest_file)
                processed_files.append({
                    'source': config_file,
                    'dest': str(dest_file),
                    'type': 'override' if 'override' in filename.lower() else 'additional'
                })
        
        except (FileNotFoundError, PermissionError) as e:
            print(f"Error copying compose files for {project_name}: {e}")
            print(f"Skipping project {project_name}.")
            # Remove the project directory if it was just created
            if project_dir.exists() and len(list(project_dir.iterdir())) == 0:
                project_dir.rmdir()
            continue
        
        # Copy .env file if it exists and is accessible, otherwise create an example
        env_path = project.get('env_path')
        if env_path and not is_in_volume:
            try:
                dest_env = project_dir / '.env'
                shutil.copy2(env_path, dest_env)
                
                # Also create a .env.example file
                dest_env_example = project_dir / '.env.example'
                create_env_example(env_path, dest_env_example)
            except (FileNotFoundError, PermissionError) as e:
                print(f"Error copying .env file for {project_name}: {e}")
                # Continue anyway, we'll create an empty example
        
        # Always create a .env.example if requested
        if create_env_examples:
            dest_env_example = project_dir / '.env.example'
            if not dest_env_example.exists() and processed_files:
                create_empty_env_example(processed_files[0]['source'], dest_env_example)
        
        # Create a README.md with basic information
        create_readme(project_dir, project_name, project, processed_files)
        
        created_projects.append({
            'name': project_name,
            'dir': str(project_dir),
            'source': project['parent_dir'],
            'config_files': [f['source'] for f in processed_files],
            'processed_files': processed_files,
            'is_in_volume': is_in_volume
        })
        
        print(f"Created project structure for {project_name} in {project_dir}")
    
    # Clean up any temporary directories
    for temp_dir in temp_dirs_to_clean:
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Warning: Could not remove temporary directory {temp_dir}: {e}")
    
    # Add failed projects to the list of created projects
    created_projects.extend(failed_projects)
    
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


def handle_failed_extraction(project_info, target_dir):
    """
    Create a placeholder structure for projects that failed automatic extraction.
    This allows users to manually add the correct configuration later.
    
    Args:
        project_info (dict): Project information
        target_dir (str): Target directory to create the structure in
        
    Returns:
        dict: Information about the created placeholder or None if failed
    """
    project_name = project_info['name']
    target_path = Path(os.path.expanduser(target_dir))
    
    try:
        # Create the project directory
        project_dir = target_path / project_name
        
        # Handle duplicate project names
        original_project_dir = project_dir
        counter = 1
        
        while project_dir.exists():
            project_dir = original_project_dir.with_name(f"{project_name}_{counter}")
            counter += 1
            
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a placeholder compose file
        placeholder_compose = project_dir / 'compose.yml'
        with open(placeholder_compose, 'w') as f:
            f.write(f"# Placeholder compose file for {project_name}\n")
            f.write("# This file was created because automatic extraction failed\n")
            f.write("# Please replace this with the actual compose configuration\n\n")
            
            # Add information about the original files
            f.write("# Original compose files:\n")
            for config_file in project_info['config_files']:
                f.write(f"# - {config_file}\n")
                
            f.write("\n# Minimal example structure:\n")
            f.write("version: '3'\n\n")
            f.write("services:\n")
            f.write(f"  {project_name.replace('-', '_')}:\n")
            f.write("    image: example/image\n")
            f.write("    # Add your configuration here\n")
        
        # Create a README.md with instructions
        readme_path = project_dir / 'README.md'
        with open(readme_path, 'w') as f:
            f.write(f"# {project_name.replace('_', ' ').title()} (Manual Configuration Needed)\n\n")
            f.write("## Warning\n\n")
            f.write("**This project structure was created because automatic extraction failed.**\n\n")
            f.write("The original Docker Compose configuration for this project could not be automatically extracted. ")
            f.write("This can happen due to several reasons:\n\n")
            f.write("1. The compose file might contain syntax errors\n")
            f.write("2. The compose file might use variables that were not defined\n")
            f.write("3. The compose file might use extensions or features not supported by 'docker compose config'\n")
            f.write("4. Access permissions issues with the original files\n\n")
            
            f.write("## Original Configuration\n\n")
            f.write("This project was originally defined in:\n\n")
            for config_file in project_info['config_files']:
                f.write(f"- `{config_file}`\n")
            
            f.write(f"\nParent directory: `{project_info['parent_dir']}`\n\n")
            
            f.write("## Manual Setup Instructions\n\n")
            f.write("1. Copy the actual compose file content into `compose.yml`\n")
            f.write("2. Create a `.env` file if the project requires environment variables\n")
            f.write("3. Test the configuration with `docker compose up -d`\n")
        
        # Create an empty .env.example file
        env_example = project_dir / '.env.example'
        with open(env_example, 'w') as f:
            f.write("# Environment variables for this project\n")
            f.write("# Replace with actual variables needed by your compose configuration\n\n")
            f.write("# EXAMPLE_VAR=example_value\n")
        
        print(f"Created placeholder structure for {project_name} in {project_dir}")
        
        return {
            'name': project_name,
            'dir': str(project_dir),
            'source': project_info['parent_dir'],
            'config_files': project_info['config_files'],
            'is_in_volume': project_info.get('is_in_volume', False),
            'is_placeholder': True
        }
        
    except Exception as e:
        print(f"Error creating placeholder for {project_name}: {e}")
        return None


def create_readme(project_dir, project_name, project_info, processed_files):
    """
    Create a README.md file with basic information about the project.
    """
    readme_path = project_dir / 'README.md'
    
    with open(readme_path, 'w') as f:
        f.write(f"# {project_name.replace('_', ' ').title()}\n\n")
        f.write("## Description\n\n")
        f.write(f"Docker Compose configuration for {project_name}.\n\n")
        
        if project_info.get('is_in_volume', False):
            f.write("**Note:** This compose file was extracted from a Docker volume and may not include all original settings.\n\n")
        
        f.write("## Usage\n\n")
        f.write("```bash\n")
        f.write("# Copy .env.example to .env and edit with your configuration\n")
        f.write("cp .env.example .env\n")
        f.write("nano .env\n\n")
        f.write("# Start the containers\n")
        f.write("docker compose up -d\n")
        f.write("```\n\n")
        
        f.write("## Original Configuration\n\n")
        f.write("This project was created from the following files:\n\n")
        for file_info in processed_files:
            file_type = file_info['type'].capitalize()
            f.write(f"- **{file_type}**: `{file_info['source']}` → `{os.path.basename(file_info['dest'])}`\n")
        
        f.write(f"\nParent directory: `{project_info['parent_dir']}`\n")


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
    parser.add_argument(
        '--no-handle-failed',
        action='store_false',
        dest='handle_failed',
        help='Do not create placeholder structures for failed extractions'
    )
    
    args = parser.parse_args()
    
    if args.use_filesystem_only:
        print(f"Searching for Docker Compose files in: {', '.join(args.fallback_search_dirs)}")
        if args.fallback_exclude_dirs:
            print(f"Excluding directories: {', '.join(args.fallback_exclude_dirs)}")
        projects = find_compose_files_in_filesystem(args.fallback_search_dirs, args.fallback_exclude_dirs)
    else:
        print("Finding Docker Compose projects using Docker Compose CLI...")
        projects = find_compose_projects_via_cli()
        
        # Filter out volume files if requested
        if args.skip_volume_files:
            original_count = len(projects)
            projects = [p for p in projects if not p.get('is_in_volume', False)]
            skipped_count = original_count - len(projects)
            if skipped_count > 0:
                print(f"Skipped {skipped_count} compose projects stored in Docker volumes.")
    
    print(f"Found {len(projects)} Docker Compose project(s)")
    
    if not projects:
        print("No Docker Compose projects found. Exiting.")
        return
    
    created_projects = create_project_structure(
        projects, 
        args.target_dir,
        args.create_env_examples,
        args.handle_failed
    )
    
    print(f"\nCreated {len(created_projects)} project(s) in {os.path.expanduser(args.target_dir)}")
    
    # Create a summary file
    summary_path = Path(os.path.expanduser(args.target_dir)) / 'SUMMARY.md'
    with open(summary_path, 'w') as f:
        f.write("# Docker Compose Projects Summary\n\n")
        f.write("| Project | Source Location | Config Files | In Volume | Target Directory | Status |\n")
        f.write("|---------|-----------------|--------------|-----------|------------------|--------|\n")
        
        for project in created_projects:
            config_files_str = ", ".join(os.path.basename(f) for f in project['config_files'])
            volume_status = "Yes" if project.get('is_in_volume', False) else "No"
            status = "Placeholder (Manual config needed)" if project.get('is_placeholder', False) else "Complete"
            f.write(f"| {project['name']} | {project['source']} | {config_files_str} | {volume_status} | {project['dir']} | {status} |\n")
    
    print(f"Created summary file at {summary_path}")


if __name__ == "__main__":
    main()
