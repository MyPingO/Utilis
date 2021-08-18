from pathlib import Path

# to delete empty directories when empty folders are not needed
def delete_empty_directories(directory: Path, base_path: Path) -> None:
    # base_path is the inner-most directory that acts as a stopping point
    # in the case that you accidentally delete a folder that's needed even if it's empty
    if directory == base_path:
        return
    # base case: if there is something in the current directory, return
    if any(directory.iterdir()):
        return
    # delete directort if it's empty
    directory.rmdir()
    # set the directory to it's parent i.e the directory before the current directory ---> folder1/folder2/folder3
    # where folder3 is current directory and folder2 is the parent file
    directory = directory.parent
    # run the recursive function with new directory
    delete_empty_directories(directory, base_path)
