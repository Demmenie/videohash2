import os
import random
import tempfile
from pathlib import Path
from typing import List


def get_list_of_all_files_in_dir(directory: str) -> List[str]:
    """
    Returns a list containing all the file paths(absolute path) in a directory.
    The list is sorted.

    :return: List of absolute path of all files in a directory.

    :rtype: List[str]
    """
    return sorted([(directory + filename) for filename in os.listdir(directory)])


def create_and_return_temporary_directory() -> str:
    """
    create a temporary directory where we can store the video, frames and the
    collage.

    :return: Absolute path of the empty directory.

    :rtype: str
    """
    path = os.path.join(tempfile.mkdtemp(), ("temp_storage_dir" + os.path.sep))
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


def _get_task_uid() -> str:
    """
    Returns an unique task id for the instance. Task id is used to
    differentiate the instance files from the other unrelated files.

    We want to make sure that only the instance is manipulating the instance files
    and no other process nor user by accident deletes or edits instance files while
    we are still processing.

    :return: instance's unique task id.

    :rtype: str
    """
    sys_random = random.SystemRandom()

    return "".join(
        sys_random.choice(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        )
        for _ in range(20)
    )
