#!/usr/bin/env python3
import math

def scale_rotate_translate_coord(coord, scale=1.0, rotation_deg=0.0, origin=(0, 0)):
    """
    Scale, rotate (around (0,0)) by rotation_deg degrees,
    then translate by 'origin'.
    """
    # Scale
    sx = coord[0] * scale
    sy = coord[1] * scale

    # Convert rotation
    theta = math.radians(rotation_deg)

    # Rotate about (0,0)
    rx = sx * math.cos(theta) - sy * math.sin(theta)
    ry = sx * math.sin(theta) + sy * math.cos(theta)

    # Translate
    final_x = rx + origin[0]
    final_y = ry + origin[1]

    return (final_x, final_y)


def transform_spec(spec, scale=1.0, origin=(0, 0), rotation_deg=0.0):
    """
    Transform the geometry of a spec by:
      - scaling
      - rotating around (0,0) by rotation_deg degrees
      - translating by origin
    The angle_sweep or angle dict is not automatically changed
    unless you specifically handle it below.
    """
    transformed_spec = []
    for element in spec:
        if element[0] == "bar":
            start = element[1]
            end   = element[2]

            # Transform endpoints
            new_start = scale_rotate_translate_coord(
                start, scale=scale, rotation_deg=rotation_deg, origin=origin
            )
            new_end   = scale_rotate_translate_coord(
                end,   scale=scale, rotation_deg=rotation_deg, origin=origin
            )

            if len(element) > 3:
                # Keep the dictionary if any
                transformed_element = ["bar", new_start, new_end, element[3]]
            else:
                transformed_element = ["bar", new_start, new_end]

            transformed_spec.append(transformed_element)
        else:
            # Copy other elements as-is (like "name", etc.)
            transformed_spec.append(element)

    return transformed_spec


def override_angle_sweep_in_spec(spec, new_sweep):
    """
    For each bar that has 'angle_sweep', override it with new_sweep.
    new_sweep should be a tuple (start_deg, end_deg, steps).
    """
    for element in spec:
        if element[0] == "bar" and len(element) > 3:
            style_dict = element[3]
            if 'angle_sweep' in style_dict:
                style_dict['angle_sweep'] = new_sweep
    return spec

def remove_ground_and_sweep(spec):
    """
    Return a modified spec where:
      - Bars with style='ground' are removed entirely.
      - The 'angle_sweep' key is removed if present (the bar remains).
    """
    new_spec = []
    for element in spec:
        if element[0] == "bar":
            style_dict = element[3] if len(element) > 3 and isinstance(element[3], dict) else {}

            # 1) Skip if it's a ground bar
            if style_dict.get("style") == "ground":
                continue  # do not add this bar to new_spec

            # 2) Remove angle_sweep if present
            if "angle_sweep" in style_dict:
                del style_dict["angle_sweep"]

            # If the style dict becomes empty, you can remove it entirely
            if len(element) > 3 and isinstance(element[3], dict) and not style_dict:
                # reconstruct element without style dict
                element = [element[0], element[1], element[2]]

            new_spec.append(element)
        else:
            # Keep non-"bar" entries as-is
            new_spec.append(element)

    return new_spec

def create_contra_parallelogram(
    scale=1.0,
    origin=(0, 0),
    rotation_deg=0.0,
    override_angle_sweep=None
):
    """
    Creates a 'counter parallelogram' spec, then transforms it
    (scale -> rotate -> translate).
    If override_angle_sweep is given, we override any angle_sweep in the base.
    """
    base_spec = [
        ["bar", (0.0, 0.0), (0.5, 0.866), {"angle_sweep": (0, 0, 1)}],
        ["bar", (0.5, 0.866), (1.5, -0.866)],
        ["bar", (0, 0), (2, 0.0), {"style": "ground"}],
        ["bar", (2, 0), (1.5, -0.866)],
    ]

    # If user wants to override the default angle_sweep
    if override_angle_sweep is not None:
        for element in base_spec:
            if (
                element[0] == "bar"
                and len(element) > 3
                and 'angle_sweep' in element[3]
            ):
                element[3]['angle_sweep'] = override_angle_sweep

    # Now apply the geometry transform
    return transform_spec(
        base_spec,
        scale=scale,
        origin=origin,
        rotation_deg=rotation_deg
    )
    
def create_multiplicator(
    scale=1.0,
    origin=(0, 0),
    rotation_deg=0.0,
    override_angle_sweep=None
):
    """
    Creates a 'multiplicator' spec, then transforms it
    (scale -> rotate -> translate).
    If override_angle_sweep is given, we override any angle_sweep in the base.
    """
    contra_parallelogram1 = create_contra_parallelogram()
    contra_parallelogram2 = create_contra_parallelogram(scale=0.5, rotation_deg=60.0)
    
    base_spec = [
        ["bar", (0.749988999838662, 0.433019052838329), (1.5, -0.866)],
    ]
    
    clean_contra_parallelogram2 = remove_ground_and_sweep(contra_parallelogram2)
    combined_spec = combine_specs(base_spec, contra_parallelogram1, clean_contra_parallelogram2)

    # If user wants to override the default angle_sweep
    if override_angle_sweep is not None:
        for element in combined_spec:
            if (
                element[0] == "bar"
                and len(element) > 3
                and 'angle_sweep' in element[3]
            ):
                element[3]['angle_sweep'] = override_angle_sweep

    # Now apply the geometry transform
    return transform_spec(
        combined_spec,
        scale=scale,
        origin=origin,
        rotation_deg=rotation_deg
    )


def combine_specs(*specs):
    """
    Combine multiple specs into a single list.
    """
    combined_spec = []
    for spec in specs:
        combined_spec.extend(spec)
    return combined_spec

