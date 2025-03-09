import re
import shutil
from subprocess import PIPE, Popen
from typing import Optional

from .exceptions import DidNotSupplyPathOrUrl, FFmpegUnableToGetDuration
from .videocopy import (
    _copy_video_to_video_dir,
    _create_required_dirs_and_check_for_errors,
)

# Module to determine the length of video.
# The length is found by the FFmpeg, the output of video_duration is in seconds.


def video_duration(
    url: Optional[str] = None,
    path: Optional[str] = None,
    storage_path: Optional[str] = None,
    do_not_copy: Optional[bool] = True,
    ffmpeg_path: Optional[str] = None,
) -> float:
    """
    Retrieve the exact video duration as echoed by the FFmpeg and return
    the duration in seconds. Maximum duration supported is 999 hours, above
    which the regex is doomed to fail(no match).

    :param url: A URL that leads to a video.

    :param path: Absolute path of the video file.

    :param storage_path: Optional, path to where you want to store the video.

    :param do_not_copy: Used when you want to save the video, defaults to True.

    :param ffmpeg_path: Path of the FFmpeg software if not in path.

    :return: Video length(duration) in seconds.

    :rtype: float
    """

    if not path and not url:
        raise DidNotSupplyPathOrUrl(
            "You must specify either a path or an URL of the video."
        )

    if path and url:
        raise ValueError("Specify either a path or an URL and NOT both.")

    if not ffmpeg_path:
        ffmpeg_path = str(shutil.which("ffmpeg"))

    if url:
        video_dir, video_download_dir = _create_required_dirs_and_check_for_errors(
            url=url, storage_path=storage_path
        )[0:2]

        path = _copy_video_to_video_dir(
            video_dir,
            video_download_dir,
            do_not_copy=do_not_copy,
            download_worst=True,
            url=url,
        )

    command = f'"{ffmpeg_path}" -i "{path}"'
    process = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
    output, error = process.communicate()

    match = re.search(
        r"Duration\:(\s\d?\d\d\:\d\d\:\d\d\.\d\d)\,",
        (output.decode() + error.decode()),
    )

    if match:
        duration_string = match.group(1)
    else:
        raise FFmpegUnableToGetDuration()

    hours, minutes, seconds = duration_string.strip().split(":")

    if url and path:
        cutPath = path[: path.find("/temp_storage_dir")]

        try:
            shutil.rmtree(cutPath)
        except OSError as e:
            print("Error: %s - %s." % (e.filename, e.strerror))

    return float(hours) * 60.00 * 60.00 + float(minutes) * 60.00 + float(seconds)
