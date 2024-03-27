import os
import sys
import time
from shutil import which
from pathlib import Path
from argparse import ArgumentParser, Namespace
import subprocess


class MainConfig:
    def __init__(self, user_args: Namespace):
        self.input_type = 'file' if Path(user_args.input).is_file() else 'directory'  # 'file' or 'directory'
        self.input = user_args.input  # Input directory or file path
        self.output = user_args.output  # Output directory
        self.input_extensions = None if not user_args.input_extensions else user_args.input_extensions.split(',')  # Input file extensions only for directory mode (separated by comma)
        self.output_extension = user_args.output_extension  # Output files extension

    class FFmpegGeneralSettings:
        ffmpeg_path = which('ffmpeg')
        def __init__(self):
            ffmpeg_path = {'value': None, 'default': which('ffmpeg')}  # FFmpeg binary path
            gpu_acceleration_api = {'value': None, 'default': None}  # GPU acceleration API: 'cuda', 'vaapi', 'd3d11va', 'opencl'
            gpu_acceleration_device = {'value': None, 'default': None}  # GPU acceleration device index: 0, 1, 2, ...
            threads = {'value': 0, 'default': 0}  # Number of threads to use
            overwrite_existing_files = {'value': True, 'default': True}  # Overwrite existing files
            hide_banner = {'value': True, 'default': True}  # Hide FFmpeg banner
            show_extra_debug_info = {'value': True, 'default': True}  # Show extra FFmpeg debug info

    class FFmpegRenderSettings:
        class VideoSection:
            class Arguments:
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
    pass



if __name__ == '__main__':
    # Parse command line arguments
    parser = ArgumentParser(description='MassVideoRenderer')
    parser.add_argument('-v', '--version', action='version', version='MassVideoRenderer 0.0.2')
    parser.add_argument('-i', '--input', metavar='input', type=str, required=True, help='Input directory or file path')
    parser.add_argument('-o', '--output', metavar='output', type=str, required=True, help='Output directory')
    parser.add_argument('-ies', '--input-extensions', default=None, metavar='input_extensions', type=str, required=False, help='Input file extensions only for directory mode (separated by comma)')
    parser.add_argument('-oe', '--output-extension', metavar='output_extension', type=str, required=True, help='Output files extension')
    args = parser.parse_args()
