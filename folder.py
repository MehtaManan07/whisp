import os
import shutil


# write a function that deletes all __pycache__ directories in the given path and its subdirectories
def delete_pycache(startpath):
    for root, dirs, files in os.walk(startpath):
        if "__pycache__" in dirs:
            dir_path = os.path.join(root, "__pycache__")
            print(f"Deleting {dir_path}")
            shutil.rmtree(dir_path)


delete_pycache("./app")


def list_files(startpath):
    for root, dirs, files in os.walk(startpath):
        level = root.replace(startpath, "").count(os.sep)
        indent = " " * 4 * (level)
        print("{}{}/".format(indent, os.path.basename(root)))
        subindent = " " * 4 * (level + 1)
        for f in files:
            if f.endswith(".py"):
                print("{}{}".format(subindent, f))


list_files("./app")


import os

# Folders to ignore during the scan
IGNORED_DIRS = {"venv", ".git", "__pycache__", "env", ".idea", ".pytest_cache"}


def count_lines_in_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)
    except Exception as e:
        print(f"Skipping {file_path}: {e}")
        return 0


def count_lines_in_codebase(root_dir="."):
    total_lines = 0
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Modify dirnames in place to skip ignored directories
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]

        for filename in filenames:
            if filename.endswith(".py"):
                file_path = os.path.join(dirpath, filename)
                total_lines += count_lines_in_file(file_path)
    return total_lines



root_directory = "./app"  # Change this to your FastAPI project root if needed
total = count_lines_in_codebase(root_directory)
print(f"Total number of lines in .py files: {total}")
