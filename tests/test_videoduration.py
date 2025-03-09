import os

import pytest
from videohash2.exceptions import DidNotSupplyPathOrUrl
from videohash2.videoduration import video_duration
from videohash2.utils import create_and_return_temporary_directory

this_dir = os.path.dirname(os.path.realpath(__file__))


def test_video_duration():
    video_path = (
        this_dir
        + os.path.sep
        + os.path.pardir
        + os.path.sep
        + "assets"
        + os.path.sep
        + "rocket.mkv"
    )

    assert (video_duration(path=video_path) - 52.08) < 0.1

    url = "https://raw.githubusercontent.com/demmenie/videohash2/main/assets/rocket.mkv"

    assert (video_duration(url=url) - 52.08) < 0.1

    with pytest.raises(DidNotSupplyPathOrUrl):
        video_duration(url=None, path=None)

    with pytest.raises(ValueError):
        storage_path = os.path.join(
            create_and_return_temporary_directory(),
            ("thisdirdoesnotexist" + os.path.sep),
        )
        video_duration(url="https://example.com", path=storage_path)
