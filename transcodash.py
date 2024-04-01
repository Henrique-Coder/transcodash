from sys import exit
from os import cpu_count
from shutil import which
from pathlib import Path
from typing import Any, Union
from subprocess import check_output, STDOUT, CalledProcessError
from argparse import ArgumentParser, Namespace
from webbrowser import open_new_tab as open_browser_new_tab
from pymediainfo import MediaInfo


def printdebug_class_items(class_instance: object) -> None:
    """
    [debug] Print all key-value pairs from a class instance
    :param class_instance: Class instance
    :return:
    """

    print('\n'.join([f'{key}={value}' for key, value in class_instance.__dict__.items()]))

def exit_app(exit_code: int = None) -> None:
    """
    Exit the application with an optional exit code
    :param exit_code: Exit code number
    """

    exit(exit_code)

def open_github_repository() -> None:
    """
    Open GitHub repository in the default web browser
    """

    open_browser_new_tab(AppInfo.source_code_url)

def append_to_list(raw_list: list, prefix: Any = None, value: Any = None, ignore_if_not_value: bool = False) -> list:
    """
    Append a prefix and a value to a list if the value is not None
    :param raw_list: Source list
    :param prefix: Prefix to append before the value
    :param value: Value to append after the prefix
    :param ignore_if_not_value: Ignore the value if it is None
    :return: Updated list
    """

    if isinstance(value, bool):
        return raw_list

    if ignore_if_not_value and value is None:
        return raw_list

    if prefix is not None:
        raw_list.append(str(prefix))
    if value is not None:
        raw_list.append(str(value))

    return raw_list

def retrieve_media_info(path_to_file: Any) -> Union[dict, None]:
    """
    Retrieve media information from the input file
    :param path_to_file: Path to the input file
    :return: Media information dictionary or None
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

def validate_arguments(args: Namespace) -> Namespace:
    """
    Check command line arguments, validate them, and return the updated arguments
    :param args: Command line arguments
    """

    # Checking required arguments
    input_filepath = Path(args.input_filepath).resolve()

    if not input_filepath.is_file():
        print(f'[error] Input file path argument is invalid: {input_filepath.as_posix()}')
        exit_app()

    output_filepath = Path(args.output_filepath).resolve()

    if input_filepath == output_filepath:
        print(f'[error] Output file path cannot be the same as input file path: {output_filepath.as_posix()}')
        exit_app()

    args.input_filepath = input_filepath.as_posix()

    if output_filepath.is_dir() or (output_filepath.parent == input_filepath.parent and output_filepath.exists() and not output_filepath.is_file()):
        print(f'[error] Output file path argument is invalid: {output_filepath.as_posix()}')
        exit_app()

    args.output_filepath = output_filepath.as_posix()

    # Checking optional arguments
    if not args.video_codec or not str(args.video_codec).strip(): args.video_codec = 'copy'
    elif not args.audio_codec or not str(args.audio_codec).strip(): args.audio_codec = 'copy'
    elif not args.subtitle_codec or not str(args.subtitle_codec).strip(): args.subtitle_codec = 'copy'

    # so rodar caso algum codec não seja copy
    if args.video_codec != 'copy' or args.audio_codec != 'copy' or args.subtitle_codec != 'copy':
        command_output = None

        try:
            command_output = check_output(['ffmpeg', '-codecs'], stderr=STDOUT).decode()
        except CalledProcessError as e:
            print(f'[error] Failed to check available FFmpeg codecs: {e} - Internal error: {e.output.decode()}')
            exit_app()

        if args.video_codec != 'copy' and args.video_codec not in command_output:
            print(f'[error] Chosen video codec is not available in your local FFmpeg installation: {args.video_codec}')
            exit_app()
        elif args.audio_codec != 'copy' and args.audio_codec not in command_output:
            print(f'[error] Chosen audio codec is not available in your local FFmpeg installation: {args.audio_codec}')
            exit_app()
        elif args.subtitle_codec != 'copy' and args.subtitle_codec not in command_output:
            print(f'[error] Chosen subtitle codec is not available in your local FFmpeg installation: {args.subtitle_codec}')
            exit_app()

    return args

def clean_list_items(raw_list: list) -> list:
    """
    Clean a list by removing None, empty, and whitespace items
    :param raw_list: Source list
    :return: Cleaned list
    """

    return [item for item in raw_list if item is not None and item.strip()]

class AppInfo:
    name = 'Transcodash'
    description = f'{name} is a smart CLI tool for optimal media transcoding. It analyzes your computer and the input media files, generating and executing an optimal FFmpeg command for efficient conversion with no visible loss of quality.'
    version = '0.0.1'
    source_code_url = 'https://github.com/Henrique-Coder/transcodash'

class FFmpegGeneralSettings:
    ffmpeg_path = None
    gpu_acceleration_api = None
    gpu_acceleration_device_index = None
    threads = None
    overwrite_existing_files = None
    hide_banner = None
    show_extra_debug_info = None

    def calculate_best_parameters(self) -> None:
        """
        Calculate the best FFmpeg settings based on the available system resources
        """

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
        :return: Updated list
        """

        generated_args = list()
        append_to_list(generated_args, value=self.ffmpeg_path)
        append_to_list(generated_args, prefix='-hwaccel', value=self.gpu_acceleration_api, ignore_if_not_value=True)
        append_to_list(generated_args, prefix='-hwaccel_device', value=self.gpu_acceleration_device_index, ignore_if_not_value=True)
        append_to_list(generated_args, prefix='-threads', value=self.threads, ignore_if_not_value=True)
        append_to_list(generated_args, value='-y' if self.overwrite_existing_files else None)
        append_to_list(generated_args, value='-hide_banner' if self.hide_banner else None)
        append_to_list(generated_args, value='-stats' if self.show_extra_debug_info else None)

        return generated_args

class FFmpegRenderSettings:
    def __init__(self):
        self.video_section = self.VideoSection()
        self.audio_section = self.AudioSection()
        self.subtitle_arguments = self.SubtitleArguments()
        self.metadata_arguments = self.MetadataArguments()
        self.custom_arguments = self.CustomArguments()

    def generate_cli_args(self) -> list:
        """
        Generate FFmpeg CLI arguments based on the best available settings
        :return: Updated list
        """

        generated_args = self.video_section.generate_cli_args()
        generated_args += self.audio_section.generate_cli_args()
        generated_args += self.subtitle_arguments.generate_cli_args()
        generated_args += self.metadata_arguments.generate_cli_args()
        generated_args += self.custom_arguments.generate_cli_args()

        return generated_args

    class VideoSection:
        def __init__(self):
            """
            Initialize the video section with the best available settings
            """

            self.arguments = self.Arguments()
            self.filters = self.Filters()

        def generate_cli_args(self) -> list:
            """
            Generate FFmpeg CLI arguments based on the best available settings
            :return: Updated list
            """

            generated_args = self.arguments.generate_cli_args()
            generated_args += self.filters.generate_cli_args()

            return generated_args

        class Arguments:
            codec = None  # Video codec: libsvtav1 (-c:v)
            frame_rate = None  # Video frame rate: None [30, 60, 120, ...] (-framerate)
            bit_rate = None  # Video bit rate: 0 [1m, 2m, 3m, ...] (-b:v)
            min_rate = None  # Minimum video bit rate: 1m [1m, 2m, 3m, ...] (-minrate:v)
            max_rate = None  # Maximum video bit rate: 6m [1m, 2m, 3m, ...] (-maxrate:v)
            quality = None  # Quality preset: high [high, medium, low, ...] (-quality)
            level = None  # Level: 4.0 [1.0, 2.0, 3.0, 4.0, 5.0, ...] (-level)
            tile_columns = None  # Tip: tile_columns * tile_rows = YOUR_CPU_CORES [0, 1, 2, 3, ...] (-tile_columns)
            tile_rows = None  # Tip: tile_rows * tile_columns = YOUR_CPU_CORES [0, 1, 2, 3, ...] (-tile_rows)
            profile = None  # Video profile: main [main, high, ...] (-profile:v)
            prediction = None  # Prediction mode: complex [simple, complex, ...] (-pred)
            b_frames_strategy = None  # B-frames strategy: 1 [0, 1, 2, 3, ...] (-b_strategy)
            b_frames = None  # Number of B-frames: 0 [1, 2, 3, ...] (-bf)
            pixel_format = None  # Pixel format: yuv420p [yuv420p, yuv422p, yuv444p, ...] (-pix_fmt)

            def calculate_best_parameters(self, media_info: 'MediaInfoData') -> None:
                """
                Calculate the best video parameters based on the input media file
                :param media_info: MediaInfoData object
                """

                def set_video_codec() -> None:
                    """
                    Set the best video codec based on the input media file
                    """

                    pass

                # Run all video settings calculations
                set_video_codec()

            def generate_cli_args(self) -> list:
                """
                Generate FFmpeg CLI arguments based on the best available settings
                :return: Updated list
                """

                generated_args = list()

                return generated_args

        class Filters:
            tune = None  # Tune: None [animation, film, grain, ...] (-tune)
            noise_reduction = None  # Noise reduction: None [0.1, 0.2, 0.3, ...] (-noise_reduction)
            deblock = None  # Deblocking: None [0.1, 0.2, 0.3, ...] (-deblock)
            sharpness = None  # Sharpness: None [0.1, 0.2, 0.3, ...] (-sharpness)
            gamma = None  # Gamma: None [0.1, 0.2, 0.3, ...] (-gamma)

            def calculate_best_parameters(self, media_info: 'MediaInfoData') -> None:
                """
                Calculate the best video filters based on the input media file
                :param media_info: MediaInfoData object
                """

                pass

            def generate_cli_args(self) -> list:
                """
                Generate FFmpeg CLI arguments based on the best available settings
                :return: Updated list
                """

                generated_args = list()

                return generated_args

    class AudioSection:
        def __init__(self):
            """
            Initialize the audio section with the best available settings
            """

            self.arguments = self.Arguments()
            self.filters = self.Filters()

        def generate_cli_args(self) -> list:
            """
            Generate FFmpeg CLI arguments based on the best available settings
            :return: Updated list
            """

            generated_args = self.arguments.generate_cli_args()
            generated_args += self.filters.generate_cli_args()

            return generated_args

        class Arguments:
            codec = None  # Audio codec: libopus (-c:a)
            bit_rate = None  # Audio bit rate: 128k [64k, 128k, 256k, ...] (-b:a)
            sample_rate = None  # Audio sample rate: 48000 [48000, 44100, 22050, ...] (-ar)

            def calculate_best_parameters(self, media_info: 'MediaInfoData') -> None:
                """
                Calculate the best audio parameters based on the input media file
                :param media_info: MediaInfoData object
                """

                def set_audio_codec() -> None:
                    """
                    Set the best audio codec based on the input media file
                    """

                    pass

                # Run all audio settings calculations
                set_audio_codec()

            def generate_cli_args(self) -> list:
                """
                Generate FFmpeg CLI arguments based on the best available settings
                :return: Updated list
                """

                generated_args = list()

                return generated_args

        class Filters:
            def calculate_best_parameters(self, media_info: 'MediaInfoData') -> None:
                """
                Calculate the best audio filters based on the input media file
                :param media_info: MediaInfoData object
                """

                pass

            def generate_cli_args(self) -> list:
                """
                Generate FFmpeg CLI arguments based on the best available settings
                :return: Updated list
                """

                generated_args = list()

                return generated_args

    class SubtitleArguments:
        codec = None  # Subtitle codec: webvtt (-c:s)

        def calculate_best_parameters(self, media_info: 'MediaInfoData') -> None:
            """
            Calculate the best subtitle parameters based on the input media file
            :param media_info: MediaInfoData object
            """

            def set_subtitle_codec() -> None:
                """
                Set the best subtitle codec based on the input media file
                """

                pass

            # Run all subtitle settings calculations
            set_subtitle_codec()

        def generate_cli_args(self) -> list:
            """
            Generate FFmpeg CLI arguments based on the best available settings
            :return: Updated list
            """

            generated_args = list()

            return generated_args

    class MetadataArguments:  # ---> !!! In this class, for each parameter, the value must be inside the braces "{}", to be replaced by the real value
        metadata_title = None  # Media title (-metadata title="{}")
        video_stream_title = None  # Video stream title (-metadata:s:v:0 title="{}")
        audio_stream_title = None  # Audio stream title (-metadata:s:a:0 title="{}")
        video_stream_language = None  # Video stream language (-metadata:s:v:0 language="{}")
        audio_stream_language = None  # Audio stream language (-metadata:s:a:0 language="{}")
        subtitle_stream_language = None  # Subtitle stream language (-metadata:s:s:0 language="{}")
        media_artist = None  # Media artist (-metadata artist="{}")
        media_year = None  # Media year (-metadata year="{}")
        media_genre = None  # Media genre (-metadata genre="{}")
        media_album = None  # Media album (-metadata album="{}")
        media_album_artist = None  # Media album artist (-metadata album_artist="{}")
        media_comment = None  # Media comment (-metadata comment="{}")
        media_track_number = None  # Media track number (-metadata track="{}")

        def calculate_best_parameters(self, media_info: 'MediaInfoData') -> None:
            """
            Calculate the best metadata parameters based on the input media file
            :param media_info: MediaInfoData object
            """

            pass

        def generate_cli_args(self) -> list:
            """
            Generate FFmpeg CLI arguments based on the best available settings
            :return: Updated list
            """

            generated_args = list()

            return generated_args

    class CustomArguments:
        args = None  # Custom extra FFmpeg arguments

        def generate_cli_args(self) -> list:
            """
            Generate FFmpeg CLI arguments based on the user-defined settings
            :return: Updated list
            """

            generated_args = list()

            return generated_args

class RunOnFinish:
    cmd = None  # Custom bash (depends on your OS) command to run on finish (this will be executed before power action)
    delay = None  # Delay in seconds before power action and after custom command execution
    task = None  # Power action available tasks: 'shutdown', 'restart', 'hibernate', 'sleep', 'lock', 'logout'

class MediaInfoData:
    def __init__(self, data: dict) -> None:
        """
        Initialize the MediaInfoData object with the raw data
        :param data: Raw media information data
        """

        self._data = data

    def __getattr__(self, attr: str) -> Union[Any, 'MediaInfoData', None]:
        """
        Get the value of an attribute from the raw data
        :param attr: Attribute name
        :return: Attribute value or None
        """

        if attr.startswith('_'):
            return self.__dict__.get(attr)

        value = self._data.get(attr)

        if value is not None:
            if isinstance(value, list):
                if len(value) == 1:
                    return self._wrap_value(value[0])

                return [self._wrap_value(item) for item in value]

            elif isinstance(value, dict):
                return self._wrap_value(value)

            return value

        return None

    def __getitem__(self, item: str) -> Any:
        """
        Get the value of an item from the raw data
        :param item: Item name
        :return: Item value
        """

        return self._data.get(item)

    def __repr__(self) -> str:
        """
        Return the raw data representation
        :return: Raw data representation
        """

        return repr(self._data)

    @staticmethod
    def _wrap_value(value: Any) -> Union[Any, 'MediaInfoData']:
        """
        Wrap a value in a MediaInfoData object if it is a dictionary
        :param value: Value to wrap
        :return: Wrapped value
        """

        if isinstance(value, dict):
            return MediaInfoData(value)

        return value

def app(args: Namespace) -> None:
    """
    Main application function
    :param args: Parsed command line arguments
    """

    # Validate command line arguments
    args = validate_arguments(args)

    # Retrieve media information from the input file
    media_info_raw_data = retrieve_media_info(args.input_filepath)
    media_info = MediaInfoData(media_info_raw_data)

    # Initialize FFmpeg settings, parameters, and run-on-finish tasks objects
    ffmpeg_general_settings = FFmpegGeneralSettings()
    ffmpeg_render_settings = FFmpegRenderSettings()
    run_on_finish = RunOnFinish()

    # Calculate the best FFmpeg settings and parameters
    ffmpeg_general_settings.calculate_best_parameters()
    ffmpeg_render_settings.video_section.arguments.calculate_best_parameters(media_info)
    ffmpeg_render_settings.video_section.filters.calculate_best_parameters(media_info)
    ffmpeg_render_settings.audio_section.arguments.calculate_best_parameters(media_info)
    ffmpeg_render_settings.audio_section.filters.calculate_best_parameters(media_info)
    ffmpeg_render_settings.subtitle_arguments.calculate_best_parameters(media_info)
    ffmpeg_render_settings.metadata_arguments.calculate_best_parameters(media_info)

    # Generate FFmpeg CLI arguments
    ffmpeg_cli_args = ffmpeg_general_settings.generate_cli_args()
    ffmpeg_cli_args += ffmpeg_render_settings.generate_cli_args()
    ffmpeg_cli_args.insert(1, '-i')
    ffmpeg_cli_args.insert(2, args.input_filepath)
    ffmpeg_cli_args.append(args.output_filepath)
    clean_ffmpeg_cli_args = clean_list_items(ffmpeg_cli_args)

    # Print the generated FFmpeg command
    print(args.__dict__)
    printdebug_class_items(ffmpeg_general_settings)
    print(clean_ffmpeg_cli_args)


if __name__ == '__main__':
    # Parse command line arguments and run the main application
    parser = ArgumentParser(description=AppInfo.description)
    parser.add_argument('-v', '--version', action='version', version=f'{AppInfo.name} {AppInfo.version}')
    parser.add_argument('-i', '--input-filepath',   metavar='input_filepath',  type=str, help='Input file path',           required=True)
    parser.add_argument('-o', '--output-filepath',  metavar='output_filepath', type=str, help='Output file path',          required=True)
    parser.add_argument('-c:v', '--video-codec',    metavar='video_codec',     type=str, help='Codec for video stream',    default='copy')
    parser.add_argument('-c:a', '--audio-codec',    metavar='audio_codec',     type=str, help='Codec for audio stream',    default='copy')
    parser.add_argument('-c:s', '--subtitle-codec', metavar='subtitle_codec',  type=str, help='Codec for subtitle stream', default='copy')

    app(parser.parse_args())  # CLI Command (example): py transcodash.py -i "inputs/video30.mkv" -o "inputs/video30-transcodashed.mp4" -c:v libsvtav1 -c:a libopus -c:s webvtt
