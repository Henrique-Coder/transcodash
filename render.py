import os
import subprocess
import time
import pathlib
import sys
import argparse


parser = argparse.ArgumentParser(description='MassVideoRenderer')
parser.add_argument('-v',  '--version',                        action='version', version='MassVideoRenderer v1.0.0')
parser.add_argument('-i',  '--input',                          metavar='input',            type=str, required=True,  help='Input directory',)
parser.add_argument('-o',  '--output',                         metavar='output',           type=str, required=True,  help='Output directory')
parser.add_argument('-ie', '--input-extensions', default=None, metavar='input_extensions', type=str, required=False, help='Input files extensions (separated by comma)')
parser.add_argument('-oe', '--output-extension',               metavar='output_extension', type=str, required=True,  help='Output files extension')

args = parser.parse_args()

for k, v in args.__dict__.items():
    setattr(args, k, v)


class settings:
    class general:
        input_type = 'file' if pathlib.Path.is_file(pathlib.Path(args.input)) else 'directory'  # Input type: 'file' or 'directory' [str]
        input = args.input  # Input directory or file [str]
        output = args.output  # Output directory [str]
        input_extensions = None if not args.input_extensions else args.input_extensions.split(',')  # Allowed extensions to be rendered [list]
        output_extension = args.output_extension  # Output files extension [str]

    class ffmpeg_settings:
        replace_existing_file = True  # Replace existing output file [bool = True]
        intentional_delay_between_encodings = 1  # Intentional delay (seconds) between encodings [int = 15]
        hide_ffmpeg_banner = True  # Hide FFmpeg banner [bool = True]
        show_extra_ffmpeg_debug_info = True  # Show extra FFmpeg debug info [bool = True]
        ffmpeg_log_level_debug = 'warning'  # FFmpeg log level debug [str = 'warning']

    ffmpeg_render_args = {
        'hwaccel': None,  # Hardware acceleration API [str = None] -> 'cuda', 'd3d11va', 'opencl', ...
        'hwaccel_device': None,  # Hardware acceleration device (GPU) ID [int = None] -> 0, 1, 2, ...
        'c:v': 'libsvtav1',  # Video codec [str] -> 'libsvtav1', 'libx264', 'libx265', ...
        'minrate:v': '2m',  # Minimum video bit rate [str] -> '2m', '4m', '8m', ...
        'maxrate:v': '8m',  # Maximum video bit rate [str] -> '2m', '4m', '8m', ...
        'quality': 'high',  # Quality preset [str] -> 'high', 'medium', 'low', ...
        'level': 4.0,  # Level [float] -> 1.0, 2.0, 3.0, 4.0, 5.0, ...
        'b:v': 0,  # Video bit rate [int] (0 = VBR)
        'tune': 0,  # Tune preset [str]
        'framerate': '60',  # Frame rate [str]
        'threads': 0,  # Number of threads [int = 0]
        'tile_columns': 2,  # Number of tile columns [int] -> tile_columns * tile_rows = YOUR_CPU_CORES
        'tile_rows': 4,  # Number of tile rows [int] -> tile_rows * tile_columns = YOUR_CPU_CORES
        'profile:v': 'main',  # Video profile [str] -> 'main', 'high', ...
        'pred': 'complex',  # Prediction mode [int] -> 'simple', 'complex', ...
        'b_strategy': 1,  # B-frames strategy [int] -> 0, 1, 2, 3, ...
        'bf': 2,  # Number of B-frames [int] -> 1, 2, 3, ...
        'c:a': 'libopus',  # Audio codec [str]
        'b:a': '128k',  # Audio bit rate [str]
        'ar': '48000',  # Audio sample rate [str]
        'c:s': 'webvtt',  # Subtitle codec [str]
        'pix_fmt': 'yuv444p',  # Pixel format [str] -> 'yuv420p', 'yuv422p', 'yuv444p', ...
        'sharpness': 0.5,  # Sharpness [float] -> 0.1, 0.2, 0.3, ...
        'gamma': 2.2,  # Gamma [float] -> 0.1, 0.2, 0.3, ...
        'deblock': 4,  # Deblocking [float] -> 0.1, 0.2, 0.3, ...
        'noise_reduction': 0.5,  # Noise reduction [float] -> 0.1, 0.2, 0.3, ...
        'additional_metadata': {
            'metadata title=': None,  # Title [str]
            'metadata:s:v:0 title=': None,  # Title [str]
            'metadata:s:a:0 title=': None,  # Title [str]
            'metadata:s:v:0 language=': None,  # Language [str]
            'metadata:s:a:0 language=': None,  # Language [str]
            'metadata artist=': None,  # Artist [str]
            'metadata year=': None,  # Year [str]
            'metadata genre=': None,  # Genre [str]
            'metadata album=': None,  # Album [str]
            'metadata album_artist=': None,  # Album artist [str]
            'metadata comment=': None,  # Comment [str]
            'metadata track=': None,  # Track [int]
        }
    }

    class end_action:
        mode = None  # The action when finished should be: 'shutdown', 'restart' or 'suspend' [str]
        custom_command = None  # Custom Windows bash command to be executed when finished (this will override 'mode' option) [str]
        time = 1  # Intentional delay (seconds) before executing final action (if enabled) [int = 60]


def flatten_dict(d, parent_key=str(), sep=':', skip_none=True) -> list:
    items = list()
    for k, v in d.items():
        new_key = f'{parent_key}{sep}{k}' if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep, skip_none=skip_none))
        elif v is not None or not skip_none:
            items.append((new_key, str(v) if v is not None else str()))

    return items


def render_file(input: pathlib.Path, output: pathlib.Path, now_ep_number: int, total_eps_quantity: int) -> int:
    # Creating FFmpeg arguments
    output_dir = output.absolute()
    ffmpeg_other_args = [f'-{key} {value}' if value else f'-{key}' for key, value in flatten_dict(settings.ffmpeg_render_args, sep=' ')]
    ffmpeg_other_args.insert(0, f'-i "{input.absolute()}"')

    # Adding additional arguments
    if settings.ffmpeg_settings.replace_existing_file:
        ffmpeg_other_args.insert(1, '-y')
        ffmpeg_other_args.append(f'"{output_dir}"')
    else:
        output_wo_ext = output_dir.parent / output_dir.stem
        while output_dir.exists():
            output_wo_ext = pathlib.Path(f'{output_wo_ext}_new')
            output_dir = pathlib.Path(f'{output_wo_ext}.{settings.general.output_extension}')
        ffmpeg_other_args.append(f'"{output_dir}"')

    if settings.ffmpeg_settings.hide_ffmpeg_banner:
        ffmpeg_other_args.insert(2, '-hide_banner')
    if settings.ffmpeg_settings.show_extra_ffmpeg_debug_info:
        ffmpeg_other_args.insert(2, '-stats')
    if settings.ffmpeg_settings.ffmpeg_log_level_debug:
        ffmpeg_other_args.insert(2, f'-loglevel {settings.ffmpeg_settings.ffmpeg_log_level_debug}')

    ffmpeg_other_args.insert(2, '-strict experimental')

    # Executing FFmpeg with arguments (and verifying if it was successful in the end)
    ffmpeg_path = 'ffmpeg.exe'
    ffmpeg_process = f'"{ffmpeg_path}" {" ".join(ffmpeg_other_args)}'
    print(f'[info] Queue: {now_ep_number}/{total_eps_quantity} - Running FFmpeg command: {ffmpeg_process}\n')
    ffmpeg_process = subprocess.run(ffmpeg_process, shell=True)
    print(f'\n[info] Queue: {now_ep_number}/{total_eps_quantity} - FFmpeg process finished with exit code {ffmpeg_process.returncode}!')

    return ffmpeg_process.returncode


def main() -> None:
    os.makedirs(settings.general.output, exist_ok=True)

    if settings.general.input_type == 'file':
        total_file_list = [pathlib.Path(settings.general.input)]
    else:
        total_file_list = [pathlib.Path(settings.general.input, _) for _ in os.listdir(settings.general.input)
                           if not settings.general.input_extensions or
                           _.split('.')[-1] in settings.general.input_extensions]

    total_file_quantity = len(total_file_list)
    now_ep_number = 0

    for input_file in total_file_list:
        render_start_time = time.time()
        now_ep_number += 1
        print(f'\n[info] Queue: {now_ep_number}/{total_file_quantity} - Starting transcoding of file "{input_file}"...')
        output_file = pathlib.Path(settings.general.output, f'{input_file.stem}.{settings.general.output_extension}')
        if render_file(input_file, output_file, now_ep_number, total_file_quantity) == 0:
            print(f'[success] Queue: {now_ep_number}/{total_file_quantity} - File "{input_file}" successfully transcoded! (took {time.time() - render_start_time:.2f} seconds)')
        else:
            print(f'[error] Queue: {now_ep_number}/{total_file_quantity} - File "{input_file}" failed to be transcoded! (took {time.time() - render_start_time:.2f} seconds)')

        if now_ep_number != total_file_quantity:
            print(f'[info] Waiting {settings.ffmpeg_settings.intentional_delay_between_encodings} second(s) before starting next encoding...')
            time.sleep(settings.ffmpeg_settings.intentional_delay_between_encodings)
            print('\n---')

    if settings.end_action.mode or settings.end_action.custom_command:
        print(f'[info] Waiting {settings.end_action.time} second(s) before executing final action...')
        time.sleep(settings.end_action.time)

        if settings.end_action.custom_command:
            print(f'[info] Running custom command in shell: "{settings.end_action.custom_command}"...')
            subprocess.run(settings.end_action.custom_command, shell=True)
        else:
            if not settings.end_action.mode:
                print('[info] No final action was set, exiting...')
            else:
                end_action_mode = settings.end_action.mode.lower()
                print(f'[info] Executing final action: "{end_action_mode}"...')
                if end_action_mode == 'shutdown':
                    subprocess.run('shutdown -s -t 60', shell=True)
                elif end_action_mode == 'restart':
                    subprocess.run('shutdown -r -t 60', shell=True)
                elif end_action_mode == 'suspend':
                    subprocess.run('shutdown -h -t 60', shell=True)


if __name__ == '__main__':
    main()
    sys.exit()
