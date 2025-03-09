import logging
import os
import re
import shutil
from pathlib import Path
from typing import Optional

from .downloader import Download
from .exceptions import DidNotSupplyPathOrUrl, StoragePathDoesNotExist
from .utils import (
    _get_task_uid,
    create_and_return_temporary_directory,
    get_list_of_all_files_in_dir,
)


def _copy_video_to_video_dir(
    video_dir: str,
    video_download_dir: str,
    do_not_copy: Optional[bool] = True,
    download_worst: bool = False,
    url: Optional[str] = None,
    path: Optional[str] = None,
) -> str:
    """
    Copy the video from the path to the video directory.

    Copying avoids issues such as the user or some other
    process deleting the instance files while we are still
    processing.

    If instead of the path the uploader specified an url,
    then download the video and copy the file to video
    directory.


    :return: None

    :rtype: NoneType

    :raises ValueError: If the path supplied by the end user
                        lacks an extension. E.g. webm, mkv and mp4.
    """
    video_path: str = ""

    if path:
        # create a copy of the video at self.storage_path
        match = re.search(r"\.([^.]+$)", path)

        if match:
            extension = match.group(1)

        else:
            raise ValueError("File name (path) does not have an extension.")

        video_path = os.path.join(video_dir, (f"video.{extension}"))

        if do_not_copy:
            os.symlink(os.path.abspath(path), video_path)
        else:
            shutil.copyfile(os.path.abspath(path), video_path)

    if url:
        Download(
            url,
            video_download_dir,
            worst=download_worst,
        )

        downloaded_file = get_list_of_all_files_in_dir(video_download_dir)[0]
        match = re.search(r"\.(.*?)$", downloaded_file)

        extension = "mkv"

        if match:
            extension = match.group(1)

        video_path = f"{video_dir}video.{extension}"

        if do_not_copy:
            os.symlink(os.path.abspath(downloaded_file), video_path)
        else:
            shutil.copyfile(os.path.abspath(downloaded_file), video_path)

    return video_path


def _create_required_dirs_and_check_for_errors(
    url: Optional[str] = None,
    path: Optional[str] = None,
    storage_path: Optional[str] = None,
) -> tuple:
    """
    Creates important directories before the main processing starts.

    The instance files are stored in these directories, no need to worry
    about the end user or some other processes interfering with the instance
    generated files.


    :raises DidNotSupplyPathOrUrl: If the user forgot to specify both the
                                    path and the url. One of them must be
                                    specified for creating the object.

    :raises ValueError: If user passed both path and url. Only pass
                        one of them if the file is available on both
                        then pass the path only.

    :raises StoragePathDoesNotExist: If the storage path specified by the
                                        user does not exist.

    :return: None

    :rtype: NoneType
    """
    if not path and not url:
        raise DidNotSupplyPathOrUrl(
            "You must specify either a path or an URL of the video."
        )

    if path and url:
        raise ValueError("Specify either a path or an URL and NOT both.")

    if path and not os.path.exists(path):
        raise FileNotFoundError(f"Video path '{path}' does not exists")

    if not storage_path:
        storage_path = create_and_return_temporary_directory()
    if not os.path.exists(storage_path):
        raise StoragePathDoesNotExist(f"Storage path '{storage_path}' does not exist.")

    os_path_sep = os.path.sep

    storage_path = os.path.join(storage_path, (f"{_get_task_uid()}{os_path_sep}"))

    video_dir = os.path.join(storage_path, (f"video{os_path_sep}"))
    Path(video_dir).mkdir(parents=True, exist_ok=True)

    video_download_dir = os.path.join(storage_path, (f"downloadedvideo{os_path_sep}"))
    Path(video_download_dir).mkdir(parents=True, exist_ok=True)

    frames_dir = os.path.join(storage_path, (f"frames{os_path_sep}"))
    Path(frames_dir).mkdir(parents=True, exist_ok=True)

    tiles_dir = os.path.join(storage_path, (f"tiles{os_path_sep}"))
    Path(tiles_dir).mkdir(parents=True, exist_ok=True)

    collage_dir = os.path.join(storage_path, (f"collage{os_path_sep}"))
    Path(collage_dir).mkdir(parents=True, exist_ok=True)

    horizontally_concatenated_image_dir = os.path.join(
        storage_path, (f"horizontally_concatenated_image{os_path_sep}")
    )
    Path(horizontally_concatenated_image_dir).mkdir(parents=True, exist_ok=True)

    return (
        storage_path,
        video_dir,
        video_download_dir,
        frames_dir,
        tiles_dir,
        collage_dir,
        horizontally_concatenated_image_dir,
    )
