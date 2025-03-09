import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import zipfile

try:
    import patoolib

    AVAILABLE_7Z = True
except (ImportError, ModuleNotFoundError):
    AVAILABLE_7Z = False


def get_ffmpeg_url(build=None, format=None) -> str:
    """
    Constructs an FFMPEG build download URL

    Args:
        build (str): the type of FFMPEG build you want
        format (str): whether you want a 7z or zip file
    """
    if format == "7z" and not AVAILABLE_7Z:
        raise ValueError("7z format unavailable as pyunpack and patool are not present")

    for ffbuild_name, formats in BUILDS.items():
        if not (build is None or build == ffbuild_name):
            continue

        for ffbuild_format, names in formats.items():
            if not (format is None or format == ffbuild_format):
                continue

            if names[0]:
                return (
                    f"https://gyan.dev/ffmpeg/builds/ffmpeg-{names[0]}.{ffbuild_format}"
                )
            if names[1]:
                github_version = (
                    urllib.request.urlopen(
                        "https://www.gyan.dev/ffmpeg/builds/release-version"
                    )
                    .read()
                    .decode()
                )
                assert github_version, "failed to retreive latest version from github"
                return (
                    "https://github.com/GyanD/codexffmpeg/releases/download/"
                    f"{github_version}/ffmpeg-{github_version}-{names[1]}.{ffbuild_format}"
                )

    raise ValueError(f"{build} as format {format} does not exist")


class InstallDirs:
    """
    Takes a URL and an installation directory and generates a number
    of suggested file paths.
    """

    def __init__(self, url, install_dir):
        """
        Args:
            url (str): the URL to the FFMPEG download
            install_dir (str): the directory to install FFMPEG to

        Instance Variables:
            install_dir (str): stores `install_dir` arg
            install_path (str): the actual path FFMPEG will be installed into
                (simply joins a "FFMPEG/" dir onto the `install_dir`)
            url (str): stores `url` arg
            hash_url (str): the URL of the file's expected sha256 hash
            download_dest (str): the file that the data will be downloaded into
            unzip_dest (str): the path that the downloaded file will be decompressed into
        """
        self.install_dir = os.path.abspath(install_dir)
        self.install_path = os.path.join(install_dir, "FFMPEG")
        self.url = url
        # can't get checksums from github
        self.hash_url = (
            None if url.startswith("https://github.com") else url + ".sha256"
        )
        self.download_dest = os.path.join(self.install_path, os.path.basename(self.url))
        self.unzip_dest = self.download_dest.rstrip(
            os.path.splitext(self.download_dest)[-1]
        )


def get_sha256(fname) -> str:
    hash_method = hashlib.sha256()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_method.update(chunk)
    return hash_method.hexdigest()


def make_empty_path(path, overwrite=False):
    """
    Creates a filepath and makes sure that it is empty

    Raises:
        FileExistsError: if the filepath exists AND is not empty
    """
    try:
        os.mkdir(path)
    except FileExistsError as e:
        if os.listdir(path):
            if overwrite:
                shutil.rmtree(path)
                make_empty_path(path, overwrite=False)
            else:
                raise FileExistsError(
                    "install directory exists and is not empty"
                ) from e


class Downloader:
    def __init__(self, url, destination, hash_url=None, mode="default"):
        """
        Args:
            url (str): the URL of the resource to download
            destination (str): the filepath to save the data to
            hash_url (str): the URL containing the file's expected hash
        """
        self.url = url
        self.destination = destination
        if hash_url is not None:
            self.hash = urllib.request.urlopen(hash_url).read().decode()
        else:
            self.hash = None
        self.mode = mode

        with urllib.request.urlopen(self.url) as data:
            self.size = data.length

    def download(self):
        """
        Downloads the file

        Raises:
            ValueError: if the expected hash does not match the downloaded file's hash
        """
        self.failed = False
        try:
            if self.mode == "windows":
                subprocess.check_output(
                    [
                        "powershell",
                        "-Command",
                        "Invoke-WebRequest",
                        self.url,
                        "-OutFile",
                        self.destination,
                    ]
                )
            elif self.mode == "wget":
                # use command prompt because powershell aliases wget to Invoke-WebRequest, which is much slower
                try:
                    subprocess.check_output(
                        ["cmd", "/c", "wget", self.url, "-O", self.destination, "-q"]
                    )
                except (FileNotFoundError, subprocess.CalledProcessError) as e:
                    print(
                        "Error calling wget:",
                        e.stderr if isinstance(e, subprocess.CalledProcessError) else e,
                    )
                    raise Exception(
                        "Call to wget failed."
                        " By default Windows sets wget as an alias of Invoke-WebRequest."
                        " Make sure you have GNU wget installed and on your PATH"
                    ) from e
            elif self.mode == "curl":
                # again, use CMD because of the alias problem. Don't need correct version warning here
                # since windows now ships with curl
                subprocess.check_output(
                    ["cmd", "/c", "curl", "-sLo", self.destination, self.url]
                )
            else:
                with open(self.destination, "wb") as f:
                    with urllib.request.urlopen(self.url) as data:
                        while chunk := data.read(4096):
                            f.write(chunk)

            if self.hash is None:
                return

            if self.hash != get_sha256(self.destination):
                self.failed = True
                raise ValueError("downloaded file does not match expected hash")
        except Exception:
            self.failed = True
            raise

    def progress(self) -> int:
        """Returns number of downloaded bytes"""
        if not os.path.isfile(self.destination):
            return 0
        return os.path.getsize(self.destination)


def download_ffmpeg(dirs: InstallDirs, mode: str):
    """Download the ffmpeg archive and print progress to the console"""
    print_progress = lambda: print(  # noqa E731
        f"Progress: {downloader.progress() / 10**6:.2f}MB / {downloader.size / 10**6:.2f}MB"
    )
    downloader = Downloader(dirs.url, dirs.download_dest, dirs.hash_url, mode=mode)
    dl_thread = threading.Thread(target=downloader.download, daemon=True)
    dl_thread.start()
    time.sleep(1)
    while dl_thread.is_alive():
        print_progress()
        time.sleep(5)
    time.sleep(1)
    if downloader.failed:
        sys.exit(1)
    print_progress()


def decompress(path, destination):
    """Decompresses `path` into `destination`"""
    if path.endswith(".zip"):
        with zipfile.ZipFile(path) as f:
            f.extractall(destination)
    else:
        os.mkdir(destination)
        patoolib.extract_archive(path, outdir=destination)


def move_ffmpeg_exe_to_top_level(top_level):
    """
    Finds the `bin/ffmpeg.exe` file in a directory tree and moves it to
    the top-level of that tree.
    EG: `C:/FFMPEG/ffmpeg-release-essentials/bin/ffmpeg.exe` -> `C:/FFMPEG/bin/ffmpeg.exe`.

    Args:
        top_level (str): the tree to search
    """
    for root, _, files in os.walk(top_level):
        for file in files:
            if file == "ffmpeg.exe":
                base_path = os.path.abspath(os.path.join(root, ".."))
                to_remove = os.listdir(top_level)

                for item in os.listdir(base_path):
                    shutil.move(os.path.join(base_path, item), top_level)

                for item in to_remove:
                    item = os.path.join(top_level, item)
                    if os.path.isdir(item):
                        shutil.rmtree(item)
                    else:
                        os.remove(item)
                break


def add_path_to_environment(path):
    """Adds a filepath to the users PATH variable after asking the user's consent"""
    os_path = os.environ["path"]
    if not os_path.endswith(";"):
        os_path += ";"
    command = f'[Environment]::SetEnvironmentVariable("Path","{os_path}{path}","User")'
    print("\n\n")
    print(command)
    print()
    try:
        subprocess.check_output(["powershell", command])
    except subprocess.CalledProcessError as e:
        print(e.stdout.decode())


BUILDS = {
    # format = { [name]: { [format]: ([gyan name], [github name]) } }
    "release-full": {"7z": ("release-full", "full_build"), "zip": (None, "full_build")},
    "release-full-shared": {
        "7z": ("release-full-shared", "full_build-shared"),
        "zip": (None, "full_build-shared"),
    },
    "release-essentials": {
        "7z": ("release-essentials", "essentials_build"),
        "zip": ("release-essentials", "essentials_build"),
    },
    "git-essentials": {"7z": ("git-essentials", None)},
    "git-full": {"7z": ("git-full", None)},
}

INSTALL_DIR = "C:\\"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--install-dir",
        type=str,
        default=INSTALL_DIR,
        help=f"The path to install FFMPEG to (default is {INSTALL_DIR})",
    )
    parser.add_argument(
        "--build",
        type=str,
        help="The build of FFMPEG to install",
        choices=list(BUILDS.keys()),
        default="release-full",
    )
    parser.add_argument(
        "--format",
        choices=("7z", "zip"),
        default="zip" if not AVAILABLE_7Z else "7z",
        help="Preferred file format",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing install",
        default=False,
    )
    parser.add_argument(
        "--downloader",
        choices=("default", "windows", "wget", "curl"),
        default="default",
        help=(
            "Control how files are downloaded."
            ' "default" will use python libraries to download, "windows" will use Invoke-WebRequest,'
            ' "wget" and "curl" will attempt to use their respective CLI utilities'
        ),
    )
    args = parser.parse_args()

    dirs = InstallDirs(get_ffmpeg_url(args.build, args.format), args.install_dir)

    print(f"Making install dir {dirs.install_path!r}")
    make_empty_path(dirs.install_path, overwrite=args.overwrite)

    print(f"Downloading {dirs.url!r} to {dirs.download_dest!r}")
    download_ffmpeg(dirs, args.downloader)

    print(f"Unzipping {dirs.download_dest!r} to {dirs.unzip_dest!r}")
    decompress(dirs.download_dest, dirs.unzip_dest)

    print(f"Move bin/ffmpeg.exe to top level of {dirs.install_path!r}")
    move_ffmpeg_exe_to_top_level(dirs.install_path)

    print(f"FFMPEG installed to {dirs.install_path!r}")

    add_path_to_environment(os.path.abspath(os.path.join(dirs.install_path, "bin")))
