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
# find all obj files in this folder. If the obj file has a corresponding mtl file,
# then load the mtl file and assign it to the obj file. If the obj file does not have a corresponding mtl file,
# then create a new material and assign it to the obj file.

import os

import numpy as np
import trimesh


def scale_mesh(
    input_file: str,
    output_file: str,
    scale_factor: float = 1.0,
    scale_all: bool = False,
    bound_type: str = "cube",
    show: bool = False,
    center_mesh: bool = False,
    align_mesh: bool = False,
):
    mesh = trimesh.load(input_file)
    print(f"Mesh loaded from {input_file}, fit to scale {scale_factor} with bounding box type {bound_type}")
    if center_mesh:
        print("Centering mesh at origin")
        print(f"Mesh center of mass: {mesh.center_mass}")
        mesh.vertices -= mesh.center_mass

    # Calculate the bounding box size
    if bound_type == "cube":
        bbox_min = mesh.bounds[0]
        bbox_max = mesh.bounds[1]
        bbox_size = bbox_max - bbox_min
        mesh_size = bbox_size.max()
        bounding_object = mesh.bounding_box_oriented
    elif bound_type == "sphere":
        bounding_object = mesh.bounding_sphere
        mesh_size = bounding_object.primitive.radius * 2
    else:
        msg = f"Unknown bounding box type {bound_type}"
        raise ValueError(msg)

    # Determine the scaling factor (1 divided by the largest dimension)

    # Scale the mesh
    if scale_all:
        # Scale each axis so the OBB has equal extents
        scale_factors = 1.0 / mesh.bounding_box_oriented.extents
        scale_matrix = np.diag(scale_factors)
        print(f"Mesh size is {mesh_size}, Scaling factors: {scale_factors}")
        mesh.apply_scale(scale_matrix)
    else:
        scaling_factor = 1.0 / mesh_size
        print(f"Mesh size is {mesh_size}, Scaling factor: {scaling_factor}")
        mesh.apply_scale(scaling_factor)

    # Identify the smallest axis
    obb = mesh.bounding_box_oriented
    obb_extents = obb.extents
    print(f"OBB extents: {obb_extents}")
    smallest_axis_index = np.argmin(obb_extents)
    print(f"Smallest axis index: {smallest_axis_index}")

    # smallest_axis_vector = obb.primitive.transform[:3, smallest_axis_index]
    smallest_axis_vector = obb.primitive.transform[:3, smallest_axis_index]

    # Compute the rotation matrix to align the smallest axis with the Z-axis
    target_axis = np.array([0, 0, 1])
    rotation_axis = np.cross(smallest_axis_vector, target_axis)
    rotation_angle = np.arccos(
        np.dot(smallest_axis_vector, target_axis) / (np.linalg.norm(smallest_axis_vector) * np.linalg.norm(target_axis))
    )
    rotation_matrix = trimesh.transformations.rotation_matrix(rotation_angle, rotation_axis)

    # Apply the rotation
    if align_mesh:
        print(f"Rotation angle: {rotation_angle}, Rotation axis: {rotation_axis}")
        mesh.apply_transform(rotation_matrix)

    if show:
        # show an arrow pointing in the direction of the smallest axis
        obb = mesh.bounding_box_oriented
        obb_extents = obb.extents
        # tranformation matrix of the smallest axis
        translation_matrix = np.eye(4)
        translation_matrix[:3, 3] = obb.primitive.center
        rotation_matrix = rotation_matrix
        arrow = trimesh.creation.axis(transform=translation_matrix)

        if bound_type == "cube":
            new_bounding_object = mesh.bounding_box_oriented
        elif bound_type == "sphere":
            new_bounding_object = mesh.bounding_sphere
        new_bounding_object.visual.face_colors = [0, 1, 1, 0.3]
        scene = trimesh.scene.scene.Scene()
        scene.add_geometry(mesh)
        scene.add_geometry(new_bounding_object)
        scene.add_geometry(arrow)

        # show a small sphere at the center of the origin
        sphere = trimesh.creation.icosphere(radius=0.1)
        sphere.apply_translation([0, 0, 0])
        scene.add_geometry(sphere)

        # show the orign axis x, y, z
        axis = trimesh.creation.axis(axis_length=1.0)
        scene.add_geometry(axis)

        scene.show()

    # Save the scaled mesh to a new OBJ file
    mesh.export(output_file)
    print(f"Mesh scaled and saved to {output_file}")


def main():
    import argparse

    bound_type_choices = ["cube", "sphere"]
    parser = argparse.ArgumentParser(description="Scale mesh to fit into a given size.")
    parser.add_argument("meshes", nargs="+", help="Mesh files to scale.")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="The directory to save the scaled meshes to.",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="The scale to apply to the mesh.",
    )
    parser.add_argument(
        "--scale-all",
        action="store_true",
        help="Scale all axis to the same size.",
    )
    parser.add_argument(
        "--output-prefix",
        default="_scaled",
        help="The prefix to add to the output file names.",
    )
    parser.add_argument(
        "--bound-type",
        type=str,
        choices=bound_type_choices,
        default="cube",
        help=f"The type of bounding box to use for scaling, one of {bound_type_choices}.",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show the scaled mesh in a viewer.",
    )
    parser.add_argument(
        "--center",
        action="store_true",
        help="Center the mesh at the origin.",
    )
    parser.add_argument(
        "--align",
        action="store_true",
        help="Rotate the mesh to align with the axes, with Z as the smallest dimension.",
    )
    args = parser.parse_args()

    for mesh_file in args.meshes:
        if args.output_dir is not None:
            output_file = os.path.join(args.output_dir, os.path.basename(mesh_file))
        else:
            output_file = mesh_file
        output_file = output_file.replace(".obj", f"{args.output_prefix}.obj")
        scale_mesh(
            mesh_file,
            output_file,
            scale_factor=args.scale,
            scale_all=args.scale_all,
            bound_type=args.bound_type,
            show=args.show,
            center_mesh=args.center,
            align_mesh=args.align,
        )


if __name__ == "__main__":
    main()
