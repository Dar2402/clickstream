import os

# Define excluded directories and excluded file extensions
EXCLUDED_DIRS = {
    "__pycache__", "venv", ".venv", ".git", ".idea",
    ".mypy_cache", ".pytest_cache", "brutus-cdc",
    "bitcoind", "btc-to-kafka", "wallet_monitor/bitcoind",
    "wallet_monitor/btc-to-kafka", "wallet_monitor/logs",
    "brutus-cdc-python", 'ping.py', 'test.py', "dump_into_mongo.py", "node_modules"
    , "static", 'staticfiles',
}

EXCLUDED_FILE_EXTENSIONS = {"txt", "log", "ipynb", "json", "zip", "pyc", 'logs'}

def should_exclude_file(file_name):
    """
    Check if a file should be excluded based on its extension.
    """
    extension = file_name.split('.')[-1]
    return extension in EXCLUDED_FILE_EXTENSIONS

def print_directory_structure(start_path, indent=""):
    try:
        items = sorted([
            item for item in os.listdir(start_path)
            if item not in EXCLUDED_DIRS and not item.startswith('.')
        ])
    except PermissionError:
        # Skip directories/files we can't access
        return

    for index, item in enumerate(items):
        path = os.path.join(start_path, item)
        is_last = (index == len(items) - 1)

        # If it's a file and should be excluded, skip it
        if os.path.isfile(path) and should_exclude_file(item):
            continue

        branch = "└── " if is_last else "├── "
        print(f"{indent}{branch}{item}")

        # Recursively print subdirectories
        if os.path.isdir(path):
            extension = "    " if is_last else "│   "
            print_directory_structure(path, indent + extension)

if __name__ == "__main__":
    current_directory = os.path.basename(os.getcwd()) + '/'
    print(f"{current_directory}")
    print_directory_structure("./")

"""
import os
from pathlib import Path

def read_and_write_directory_contents(input_dir, output_file, exclude_files=None, exclude_folders=None):
    """"""
    Reads all files in the input directory and writes their content to an output file.
    
    :param input_dir: The directory to read files from.
    :param output_file: The file to write all contents to.
    :param exclude_files: List of specific files to exclude from reading.
    :param exclude_folders: List of specific folders to exclude from reading.
    """"""
    # Set default values for exclude parameters if not provided
    if exclude_files is None:
        exclude_files = []
    if exclude_folders is None:
        exclude_folders = []

    with open(output_file, 'w', encoding='utf-8') as outfile:
        # Walk through the directory
        for root, dirs, files in os.walk(input_dir):
            # Exclude directories that are in exclude_folders list
            dirs[:] = [d for d in dirs if d not in exclude_folders]
            
            for file in files:
                # Skip files in the exclude_files list
                if file.split('.')[-1] in exclude_files:
                    continue

                file_path = os.path.join(root, file)
                
                # Open the file and append its content to the output file
                try:
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        outfile.write(f"\n--- Content of {file_path} ---\n")
                        outfile.write(infile.read())
                        outfile.write("\n\n")
                except Exception as e:
                    print(f"Error reading file {file_path}: {e}")

# Example usage
if __name__ == "__main__":
    input_directory = Path.cwd() / 'btc_monitor'  # Change this to your directory
    output_file = Path.cwd() / 'btc_monitor' / 'output.txt'     # Change this to your desired output file
    
    # List of files or folders to exclude
    exclude_files = ['txt', 'another_file_to_exclude.txt', 'log', 'ipynb', 'json']
    exclude_folders = ['folder_to_exclude', 'another_folder_to_exclude']

    read_and_write_directory_contents(input_directory, output_file, exclude_files, exclude_folders)
    print(f"Content from files in {input_directory} has been written to {output_file}")

    
"""



