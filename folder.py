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
