#!/usr/bin/env python
#  Copyright (c) 2024. Jet Propulsion Laboratory. All rights reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import math
import os
from copy import copy
from pathlib import Path

import cv2
import h5py
import Imath  # another OpenEXR library
import matplotlib.pyplot as plt
import numpy as np
import OpenEXR
from PIL import Image
from tqdm import tqdm


def load_exr(file_path: str):
    """Load an EXR file and return the image data and channel names.

    Args:
    ----
        file_path (str): The path to the EXR file.

    Returns:
    -------
        np.ndarray: The image data.
        list[str]: The channel names.

    """
    # Open the EXR file
    exr_file = OpenEXR.InputFile(file_path)

    # Get the header information
    header = exr_file.header()

    # Get the data window size
    dw = header["dataWindow"]
    width = dw.max.x - dw.min.x + 1
    height = dw.max.y - dw.min.y + 1

    # Define the channels
    channels = list(header["channels"].keys())

    # Create an array to hold the image data
    img = np.zeros((height, width, len(channels)), dtype=np.float32)

    # Read the data for each channel
    for i, channel in enumerate(channels):
        channel_data = exr_file.channel(channel, Imath.PixelType(Imath.PixelType.FLOAT))
        img[:, :, i] = np.frombuffer(channel_data, dtype=np.float32).reshape((height, width))

    return img, channels


def overlay_images(
    base_image_path: str,
    overlay_image_path: str,
    output_path: str,
    scale: float = 0.1,
    rotation: float = 0,
    margin: float = 0.2,
) -> None:
    """Overlay an image on top of another image.

    Args:
    ----
        base_image_path (str): The path to the base image.
        overlay_image_path (str): The path to the overlay image.
        output_path (str): The path to save the output image.
        scale (float): The scale factor for the overlay image relative to the base image size.
        rotation (float): The rotation angle for the overlay image in degrees.
        margin (float): The margin as a percentage of the base image size.

    Output:
        Saves the combined image to the output path.

    """
    assert 0 <= scale <= 1, "Scale must be between 0 and 1"
    assert 0 <= margin <= 1, "Margin must be between 0 and 1"

    if not os.path.exists(base_image_path):
        msg = f"Base image not found: {base_image_path}"
        raise FileNotFoundError(msg)

    if not os.path.exists(overlay_image_path):
        msg = f"Overlay image not found: {overlay_image_path}"
        raise FileNotFoundError(msg)

    if margin < scale:
        print(f"Warning: margin {margin} is greater than scale {scale}, image might not be visible.")

    # Open the base image
    base_image = Image.open(base_image_path).convert("RGBA")

    # Open the overlay image
    overlay_image = Image.open(overlay_image_path).convert("RGBA")

    # Scale the overlay image to a percentage of the base image size
    base_width, base_height = base_image.size
    overlay_image = overlay_image.resize((int(base_width * scale), int(base_height * scale)), Image.Resampling.LANCZOS)

    # Rotate the overlay image
    overlay_image = overlay_image.rotate(math.degrees(rotation), expand=True)

    # Calculate position to paste the overlay image (top right corner with margin)
    overlay_width, overlay_height = overlay_image.size
    position = (
        int(base_width * (1 - margin) - overlay_width / 2),
        int(base_height * margin - overlay_height / 2),
    )

    # Create a new image with the same size as the base image and an alpha layer (transparent)
    combined_image = Image.new("RGBA", base_image.size)
    combined_image.paste(base_image, (0, 0))
    combined_image.paste(overlay_image, position, overlay_image)

    # Save the combined image
    combined_image.save(output_path, format="PNG")


def display_exr(img: np.ndarray, channels: list[str]) -> None:
    """Display an EXR image.

    Args:
    ----
        img (np.ndarray): The image data.
        channels (list[str]): The channel names.

    """
    # Plot each channel
    if len(channels) == 1:
        # write as nan values higher than 100
        img[img > 100] = np.nan

        plt.imshow(img[:, :, 0], cmap="magma")
        plt.title(f"Channel: {channels}")
        plt.colorbar()
        plt.axis("off")
    else:
        # img = np.clip(img, 0, 1)
        for i, channel in enumerate(channels):
            plt.subplot(1, len(channels), i + 1)
            img_i = img[:, :, i]
            img_i[img_i > 100] = np.nan
            plt.imshow(img_i, cmap="magma")
            plt.title(f"Channel: {channel}")
            plt.colorbar()
            plt.axis("off")

    plt.show()


def save_to_hdf5(img: np.ndarray, channels: list[str], output_file: str):
    with h5py.File(output_file, "w") as f:
        for i, channel in enumerate(channels):
            f.create_dataset(channel, data=img[:, :, i])
        f.attrs["channels"] = list(channels)


def get_frame_number(filename: str) -> int:
    """Extract the frame number from the filename.

    Args:
    ----
        filename (str): The filename of the frame to extract its number.

    """
    frame_number = int(filename.split("_")[-1].split(".")[0])
    return frame_number


def get_color_space(frame: np.ndarray) -> str:
    """Get the color space of the frame.

    Parameters
    ----------
        frame (np.ndarray): The frame to check.

    Returns
    -------
    str: The color space of the frame.

    """
    if len(frame.shape) == 2:
        return "grayscale"
    elif len(frame.shape) == 3:
        channels = frame.shape[2]
        if channels == 3:
            return "BGR"
        elif channels == 4:
            return "BGRA"
    return "unknown"


def combine_frames(
    prefixes: list[str],
    images: dict[str, dict[int, str]],
    frame_set_sorted: list,
    frame__image_size: tuple[int, int] = (640, 480),
    add_frame_text: bool = True,
    border_size: int = 4,
    border_color: tuple[int, int, int] = (0, 0, 0),
) -> list[np.ndarray]:
    """Combine the frames from multiple cameras into a single frame.

    Parameters
    ----------
        prefixes (list[str]): The prefixes of the cameras.
        images (dict[str, dict[int, str]]): The images from each camera.
        frame_set_sorted (set): The set of frame indices.
        frame__image_size (tuple[int, int]): The size of the frames.

    Returns
    -------
        list[np.ndarray]: The combined frames.

    """
    previous_frame = {}
    for prefix in prefixes:
        first_image = cv2.imread(images[prefix][frame_set_sorted[0]])
        if first_image is None:
            print(f"Could not read first frame from camera {prefix}")
            first_image = np.zeros(frame__image_size + (3,), dtype=np.uint8)
        else:
            previous_frame[prefix] = cv2.resize(first_image, frame__image_size)

    # Iterate over the frames
    output_frames = []
    for frame_index in tqdm(frame_set_sorted, desc="Reading frames..", unit="frames"):
        frames = []

        # Read each frame from each camera
        for prefix in prefixes:
            frame = cv2.imread(images[prefix][frame_index])
            # print(f"{prefix}: frame color space: {get_color_space(frame)}")
            if frame is None:
                print(f"Could not read frame {frame_index} from camera {prefix}")
                frame = previous_frame[prefix]

            if len(frame.shape) == 2:  # If the frame is grayscale, convert it to BGR
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

            # Resize the frame if necessary
            frame = cv2.resize(frame, frame__image_size)
            if add_frame_text:
                # add text "{prefix} - {frame_index}" to the bottom middle of the frame
                text = f"{prefix} - {frame_index}"
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 1
                font_thickness = 2
                text_size = cv2.getTextSize(text, font, font_scale, font_thickness)[0]
                text_x = (frame__image_size[0] - text_size[0]) // 2
                text_y = frame__image_size[1] - text_size[1] + 10
                text_color = (255, 255, 255)
                cv2.putText(
                    frame,
                    text,
                    (text_x, text_y),
                    font,
                    font_scale,
                    text_color,
                    font_thickness,
                )

            if border_size > 0:
                frame = cv2.copyMakeBorder(
                    frame,
                    border_size,
                    border_size,
                    border_size,
                    border_size,
                    cv2.BORDER_CONSTANT,
                    value=border_color,
                )
            frames.append(frame)
            previous_frame[prefix] = frame

        # Concatenate the frames side by side
        combined_frame = cv2.hconcat(frames)
        output_frames.append(copy(combined_frame))
    return output_frames


def save_video(
    output_frames: list[np.ndarray],
    output_file: str,
    fps: int = 30,
) -> None:
    """Save the frames to a video file.

    Parameters
    ----------
        output_frames (list[np.ndarray]): The frames to save.
        output_file (str): The output file to write the video to.
        frame__image_size (tuple[int, int]): The size of the frames.
        fps (int): The frames per second of the video.

    """
    # frame__image_size = (output_frames[0].shape[1], output_frames[0].shape[0])
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")  #  type: ignore[attr-defined]
    frame_combined_size = (output_frames[0].shape[1], output_frames[0].shape[0])
    print(f"Combined frame size: {frame_combined_size}")
    vidwriter = cv2.VideoWriter(output_file, fourcc, fps, frame_combined_size)
    for frame in tqdm(output_frames, desc="Writing frames..", unit="frames"):
        vidwriter.write(frame)
    vidwriter.release()
    print("Video written successfully.")


def get_images(data_dir: str, prefixes: list[str], start: int, end: int):
    print(f"Searching for images in {data_dir} for cameras {prefixes}")
    images: dict[str, dict[int, str]] = {}
    for prefix in prefixes:
        images[prefix] = {}
        for filename in os.listdir(data_dir):
            if filename.startswith(prefix) and filename.endswith(".png"):
                frame_number = get_frame_number(filename)
                if start <= frame_number and (end == -1 or frame_number <= end):
                    images[prefix][get_frame_number(filename)] = os.path.join(data_dir, filename)

        print(f"Found {len(images[prefix])} images for camera {prefix}")
    return images


def collect_frame_indices(images: dict[str, dict[int, str]]) -> list[int]:
    frame_set = set()
    for prefix in images.keys():
        frame_index_list = list(images[prefix].keys())
        for ff in frame_index_list:
            frame_set.add(ff)
    print(f"Found {len(frame_set)} frames in total")
    return sorted(frame_set)


def create_multiview_video(
    data_dir: str,
    prefixes: list[str],
    output_file: str,
    frame_image_size: tuple[int, int] = (640, 480),
    fps: int = 30,
    start: int = 0,
    end: int = -1,
) -> None:
    images = get_images(data_dir, prefixes, start, end)
    frame_set_sorted = collect_frame_indices(images)
    output_frames = combine_frames(prefixes, images, frame_set_sorted, frame_image_size)
    save_video(output_frames, output_file, fps)


def export_combine_frames(
    data_dir: str,
    prefixes: list[str],
    output_dir: str | None = None,
    output_prefix: str = "combined",
    frame_image_size: tuple[int, int] = (640, 480),
    start: int = 0,
    end: int = -1,
    collage: bool = False,
) -> None:
    images = get_images(data_dir, prefixes, start, end)
    for prefix in prefixes:
        if len(images[prefix]) == 0:
            print(f"No images found for camera {prefix}")
            return

    frame_set_sorted = collect_frame_indices(images)
    output_frames = combine_frames(prefixes, images, frame_set_sorted, frame_image_size)
    if output_dir is None:
        output_dir = data_dir
    if collage:
        output_filename = str(Path(output_dir) / Path(output_prefix + ".png"))
        save_collage(output_frames, output_filename)
    else:
        save_frames(output_frames, output_dir, output_prefix)


def save_collage(
    output_frames: list[np.ndarray],
    output_filename: str = "collage.png",
    border_size: int = 10,
    border_color: tuple[int, int, int] = (0, 0, 0),
) -> None:
    # create a collage more or less square
    n_cols = int(np.sqrt(len(output_frames)))
    n_rows = len(output_frames) // n_cols

    if border_size > 0:
        for i, frame in enumerate(output_frames):
            output_frames[i] = cv2.copyMakeBorder(
                frame,
                border_size,
                border_size,
                border_size,
                border_size,
                cv2.BORDER_CONSTANT,
                value=border_color,
            )

    for r in range(n_rows):
        for c in range(n_cols):
            if c == 0:
                row = output_frames[r * n_cols]
            else:
                row = cv2.hconcat([row, output_frames[r * n_cols + c]])
        if r == 0:
            collage = row
        else:
            collage = cv2.vconcat([collage, row])

    # collage = cv2.vconcat(output_frames)
    # create directory if it does not exist
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    cv2.imwrite(output_filename, collage)
    print(f"Saved collage to {output_filename}")


def save_frames(output_frames: list[np.ndarray], output_dir: str, output_prefix: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    for i, frame in enumerate(output_frames):
        output_file = f"{output_dir}/{output_prefix}_{i:04d}.png"
        cv2.imwrite(output_file, frame)
        print(f"Saved frame {i} to {output_file}")
