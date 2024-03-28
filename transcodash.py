import os
import sys
import time
import string
from sys import exit
from os import cpu_count
from shutil import which
from pathlib import Path
from typing import Any, Union
from subprocess import check_output, STDOUT, CalledProcessError
from argparse import ArgumentParser, Namespace
from webbrowser import open_new_tab as open_browser_new_tab
from pymediainfo import MediaInfo


def debug_print_dict_items(class_instance: object) -> None:
    print('\n'.join([f'{key}={value}' for key, value in class_instance.__dict__.items()]))

def exit_app(exit_code: int = None) -> None:
    """
    Exit the application with a specific exit code
    :param exit_code:
    """

    exit(exit_code)

def open_github_repository() -> None:
    """
    Open GitHub repository in the default web browser
    """

    open_browser_new_tab(AppInfo.source_code_url)

def append_to_list(raw_list: list, value: Any, prefix: Any, ignore_none_value: bool = False) -> list:
    if isinstance(value, bool):
        return raw_list

    if ignore_none_value and value is None:
        return raw_list

    if prefix is not None:
        raw_list.append(str(prefix))
    if value is not None:
        raw_list.append(str(value))

    return raw_list

def retrieve_media_info(path_to_file: Any) -> Union[dict, None]:
    """
    Retrieve media information from a file using pymediainfo library
    :param path_to_file:
    :return: dict
    """

    try:
        media_info = MediaInfo.parse(path_to_file)
        media_info_data = {'video': list(), 'audio': list(), 'subtitle': list(), 'metadata': list()}

        for track in media_info.tracks:
            track_info = dict()
            for key, value in track.__dict__.items():
                if key != '_mediainfo':
                    track_info[key] = value
            if track.track_type == 'Video':
                media_info_data['video'].append(track_info)
            elif track.track_type == 'Audio':
                media_info_data['audio'].append(track_info)
            elif track.track_type == 'Text':
                media_info_data['subtitle'].append(track_info)
            else:
                media_info_data['metadata'].append(track_info)

        return media_info_data
    except BaseException as e:
        print(f'[error] Failed to retrieve media information from the input file: {path_to_file.as_posix()} - Internal error: {e}')
        exit_app()

class AppInfo:
    name = 'Transcodash'
    version = '0.1.0'
    source_code_url = 'https://github.com/Henrique-Coder/transcodash'

class UserArgs:
    def __init__(self, user_args: Namespace):
        self.input_filepath = user_args.input_filepath
        self.output_filepath = user_args.output_filepath
        self.video_codec = user_args.video_codec

    def check_arguments(self) -> None:
        _input_filepath = Path(self.input_filepath).resolve()
        _output_filepath = Path(self.output_filepath).resolve()

        if not Path(self.input_filepath).is_file() or not Path(self.input_filepath).exists():
            print(f'[error] Input file path argument is invalid: {_input_filepath.as_posix()}')
            exit_app()

        self.input_filepath = _input_filepath.as_posix()
        self.output_filepath = _output_filepath.as_posix()

        command_output = None

        try:
            command_output = check_output(['ffmpeg', '-codecs'], stderr=STDOUT).decode()
        except CalledProcessError as e:
            print(f'[error] Failed to check available FFmpeg codecs: {e} - Internal error: {e.output.decode()}')
            exit_app()

        if self.video_codec not in command_output:
            print(f'[error] Chosen video codec is not available in your local FFmpeg installation: {self.video_codec}')
            exit_app()

class MediaInfoData:
    raw_data = None

class FFmpegGeneralSettings:
    ffmpeg_path = None
    gpu_acceleration_api = None
    gpu_acceleration_device_index = None
    threads = None
    overwrite_existing_files = None
    hide_banner = None
    show_extra_debug_info = None

    def calculate_best_parameters(self) -> None:
        def set_ffmpeg_path() -> None:
            """
            Set absolute path to FFmpeg binary file if available
            """

            _ffmpeg_path = which('ffmpeg')

            if not _ffmpeg_path:
                self.ffmpeg_path = None

            self.ffmpeg_path = Path(_ffmpeg_path).resolve().as_posix()

        def set_gpu_acceleration_api_and_device_index() -> None:
            """
            Set ideal GPU acceleration API and device index if available
            """

            # Feature unavailable at the moment. (Please ignore this function)
            self.gpu_acceleration_api = None
            self.gpu_acceleration_device_index = None
            return
            # ...

            _gpu_acceleration_api = None
            _gpu_acceleration_device_index = None

            if which('nvidia-smi'):
                _gpu_acceleration_api = 'cuda'
            elif which('vainfo'):
                _gpu_acceleration_api = 'vaapi'
            elif which('dxva2'):
                _gpu_acceleration_api = 'd3d11va'
            elif which('clinfo'):
                _gpu_acceleration_api = 'opencl'
            else:
                self.gpu_acceleration_api = _gpu_acceleration_api
                self.gpu_acceleration_device_index = _gpu_acceleration_device_index

            if _gpu_acceleration_api:
                self.gpu_acceleration_api = _gpu_acceleration_api
                self.gpu_acceleration_device_index = 0

        def set_threads() -> None:
            """
            Set ideal number of threads to use
            """

            _threads = cpu_count()

            if not _threads or _threads <= 1:
                self.threads = None
            else:
                self.threads = _threads - 1

        def set_other_settings() -> None:
            """
            Set default values for other FFmpeg settings
            """

            # Overwrite existing files
            self.overwrite_existing_files = True

            # Hide FFmpeg banner
            self.hide_banner = True

            # Show extra FFmpeg debug info
            self.show_extra_debug_info = True

        set_ffmpeg_path()
        set_gpu_acceleration_api_and_device_index()
        set_threads()
        set_other_settings()

    def generate_cli_args(self) -> list:
        """
        Generate FFmpeg CLI arguments based on the best available settings
        :return: list
        """

        generated_args = list()
        append_to_list(generated_args, self.ffmpeg_path, None)
        append_to_list(generated_args, self.gpu_acceleration_api, '-hwaccel', True)
        append_to_list(generated_args, self.gpu_acceleration_device_index, '-hwaccel_device', True)
        append_to_list(generated_args, self.threads, '-threads', True)
        if self.overwrite_existing_files: append_to_list(generated_args, None, '-y')
        if self.hide_banner: append_to_list(generated_args, None, '-hide_banner')
        if self.show_extra_debug_info: append_to_list(generated_args, None, '-stats')

        return generated_args

class FFmpegRenderSettings:
    class VideoSection:
        class Arguments():
            def __init__(self):
                codec = {'value': 'libsvtav1', 'default': None, 'arg': '-c:v {}'}  # Video codec
                frame_rate = {'value': None, 'default': None, 'arg': '-framerate'}  # Video frame rate: 30, 60, 120, ...
                bit_rate = {'value': 0, 'default': None, 'arg': '-b:v'}  # Video bit rate: (0 = VBR)
                min_rate = {'value': 1, 'default': None, 'arg': '-minrate:v'}  # Minimum video bit rate: 1m, 2m, 3m, ...
                max_rate = {'value': 6, 'default': None, 'arg': '-maxrate:v'}  # Maximum video bit rate: 1m, 2m, 3m, ...
                quality = {'value': 'high', 'default': None, 'arg': '-quality'}  # Quality preset: 'high', 'medium', 'low', ...
                level = {'value': 4.0, 'default': None, 'arg': '-level'}  # Level: 1.0, 2.0, 3.0, 4.0, 5.0, ...
                tile_columns = {'value': 2, 'default': None, 'arg': '-tile_columns'}  # Tip: tile_columns * tile_rows = YOUR_CPU_CORES
                tile_rows = {'value': 4, 'default': None, 'arg': '-tile_rows'}  # Tip: tile_rows * tile_columns = YOUR_CPU_CORES
                profile = {'value': 'main', 'default': None, 'arg': '-profile:v'}  # Video profile: 'main', 'high', ...
                prediction = {'value': 'complex', 'default': None, 'arg': '-pred'}  # Prediction mode: 'simple', 'complex', ...
                b_frames_strategy = {'value': 1, 'default': None, 'arg': '-b_strategy'}  # B-frames strategy: 0, 1, 2, 3, ...
                b_frames = {'value': 0, 'default': None, 'arg': '-bf'}  # Number of B-frames: 1, 2, 3, ...
                pixel_format = {'value': 'yuv420p', 'default': None, 'arg': '-pix_fmt'}  # Pixel format: 'yuv420p', 'yuv422p', 'yuv444p', ...

        class Filters:
            def __init__(self):
                tune = {'value': None, 'default': None, 'arg': '-tune'}  # Tune: 'animation', 'film', 'grain', ...
                noise_reduction = {'value': None, 'default': None, 'arg': '-noise_reduction'}  # Noise reduction: 0.1, 0.2, 0.3, ...
                deblock = {'value': None, 'default': None, 'arg': '-deblock'}  # Deblocking: 0.1, 0.2, 0.3, ...
                sharpness = {'value': None, 'default': None, 'arg': '-sharpness'}  # Sharpness: 0.1, 0.2, 0.3, ...
                gamma = {'value': None, 'default': None, 'arg': '-gamma'}  # Gamma: 0.1, 0.2, 0.3, ...

    class AudioSection:
        class Arguments:
            def __init__(self):
                codec = {'value': 'libopus', 'default': None, 'arg': '-c:a'}  # Audio codec
                bit_rate = {'value': '128k', 'default': None, 'arg': '-b:a'}  # Audio bit rate: '64k', '128k', '256k', ...
                sample_rate = {'value': '48000', 'default': None, 'arg': '-ar'}  # Audio sample rate: '48000', '44100', '22050', ...

        class Filters:
            def __init__(self):
                pass

    class SubtitleArguments:
        def __init__(self):
            codec = {'value': 'webvtt', 'default': None, 'arg': '-c:s'}

    class MetadataArguments:
        def __init__(self):
            media_title = {'value': None, 'default': None, 'arg': '-metadata title='}  # Media title
            video_stream_title = {'value': None, 'default': None, 'arg': '-metadata:s:v:0 title='}  # Video stream title
            audio_stream_title = {'value': None, 'default': None, 'arg': '-metadata:s:a:0 title='}  # Audio stream title
            video_stream_language = {'value': None, 'default': None, 'arg': '-metadata:s:v:0 language='}  # Video stream language
            audio_stream_language = {'value': None, 'default': None, 'arg': '-metadata:s:a:0 language='}  # Audio stream language
            subtitle_stream_language = {'value': None, 'default': None, 'arg': '-metadata:s:s:0 language='}  # Subtitle stream language
            media_artist = {'value': None, 'default': None, 'arg': '-metadata artist='}  # Media artist
            media_year = {'value': None, 'default': None, 'arg': '-metadata year='}  # Media year
            media_genre = {'value': None, 'default': None, 'arg': '-metadata genre='}  # Media genre
            media_album = {'value': None, 'default': None, 'arg': '-metadata album='}  # Media album
            media_album_artist = {'value': None, 'default': None, 'arg': '-metadata album_artist='}  # Media album artist
            media_comment = {'value': None, 'default': None, 'arg': '-metadata comment='}  # Media comment
            media_track_number = {'value': None, 'default': None, 'arg': '-metadata track='}  # Media track number

    class CustomArguments:
        def __init__(self):
            custom_args = {'value': None, 'default': None}

class RunOnFinish:
        def __init__(self):
            cmd = {'value': None, 'default': None}  # Custom bash command to run on finish (this will be executed before power action)
            delay = {'value': None, 'default': 5}  # Delay in seconds before power action and after custom command execution
            task = {'value': None, 'default': None}  # Power action available tasks: 'shutdown', 'restart', 'hibernate', 'sleep', 'lock'

def main_app(user_args: Namespace):
    # Initialize UserArgs class
    user_args = UserArgs(user_args)
    user_args.check_arguments()

    # Initialize other classes
    media_info_data = MediaInfoData()
    ffmpeg_general_settings = FFmpegGeneralSettings()
    ffmpeg_render_settings = FFmpegRenderSettings()
    run_on_finish = RunOnFinish()

    # Retrieve media information from the input file
    media_info_data.raw_data = retrieve_media_info(user_args.input_filepath)

    # Calculate the best FFmpeg settings
    ffmpeg_general_settings.calculate_best_parameters()

    # Generate FFmpeg CLI arguments
    ffmpeg_cli_args = ffmpeg_general_settings.generate_cli_args()
    print(ffmpeg_cli_args)


if __name__ == '__main__':
    # Parse command line arguments and run the main application
    parser = ArgumentParser(description=f"{AppInfo.name} is a smart CLI tool for optimal media transcoding. It analyzes your computer and the input media files, generating and executing an optimal FFmpeg command for efficient conversion with no visible loss of quality.")
    parser.add_argument('-v', '--version', action='version', version=f'{AppInfo.name} {AppInfo.version}')
    parser.add_argument('-gh', '--github', action='store_true', help=f'Open {AppInfo.name} GitHub repository in your default web browser')
    parser.add_argument('-i', '--input-filepath', metavar='input_filepath', type=str, help='Input file path')
    parser.add_argument('-o', '--output-filepath', metavar='output_filepath', type=str, help='Output file path')
    parser.add_argument('-c:v', '--video-codec', metavar='video_codec', type=str, help='Codec for video stream')
    args = parser.parse_args()

    if args.github:
        open_github_repository()
    elif args.input_filepath and args.output_filepath:
        main_app(args)
    else:
        parser.print_help()
