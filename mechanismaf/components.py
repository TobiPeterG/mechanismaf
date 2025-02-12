#!/usr/bin/env python3
import math

def round_coord(coord, decimal=3):
    """
    Round the components of a coordinate tuple to a fixed number of decimal places.

    This function converts each element of the coordinate to a float (if not already)
    and rounds it to the specified number of decimal places.

    Parameters
    ----------
    coord : tuple of int or float
        A coordinate given as a tuple (e.g., (x, y)).
    decimal : int, optional
        The number of decimal places to round to. Default is 3.

    Returns
    -------
    tuple of float
        A new coordinate tuple with each value rounded to the specified precision.
    """
    return tuple(round(float(x), decimal) for x in coord)

def transform_follow_points(points, scale=1.0, rotation_deg=0.0, origin=(0, 0)):
    """
    Transform a list of follow points by scaling, rotating, and translating them.

    This function applies the same transformation (scaling, rotation, and translation)
    used for the mechanism geometry to each point in the input list. The transformation
    is applied in the following order: scale, then rotate (about (0,0)), then translate.

    Parameters
    ----------
    points : list of tuple of int or float
        A list of coordinate tuples representing the follow points.
    scale : float, optional
        The scaling factor applied to each coordinate. Default is 1.0.
    rotation_deg : float, optional
        The rotation angle in degrees (about (0,0)) to apply. Default is 0.0.
    origin : tuple of int or float, optional
        The translation offset (x, y) to apply after rotation. Default is (0, 0).

    Returns
    -------
    list of tuple of float
        A new list of transformed coordinate tuples.
    """
    return [
        scale_rotate_translate_coord(pt, scale=scale, rotation_deg=rotation_deg, origin=origin)
        for pt in points
    ]

def scale_rotate_translate_coord(coord, scale=1.0, rotation_deg=0.0, origin=(0, 0)):
    """
    Apply a combined scale, rotation, and translation to a coordinate.

    The transformation is performed in three steps:
      1. Scale the coordinate by multiplying both components by 'scale'.
      2. Rotate the scaled coordinate around (0,0) by 'rotation_deg' degrees.
      3. Translate the rotated coordinate by adding the 'origin' offset.

    Parameters
    ----------
    coord : tuple of int or float
        The original coordinate (x, y).
    scale : float, optional
        Scaling factor. Default is 1.0.
    rotation_deg : float, optional
        Rotation angle in degrees. Default is 0.0.
    origin : tuple of int or float, optional
        The translation offset (x, y). Default is (0, 0).

    Returns
    -------
    tuple of float
        The transformed coordinate.
    """
    # Scale
    sx = coord[0] * scale
    sy = coord[1] * scale

    # Convert rotation angle from degrees to radians
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
    Transform the geometry of a specification by scaling, rotating, and translating its coordinates.

    This function processes a specification list (typically containing bar definitions and other
    elements such as mechanism names). For each bar element, the start and end coordinates are transformed
    using the provided scale, rotation, and translation parameters. Other parameters (e.g., angle sweeps)
    in the optional dictionary are preserved without modification.

    Parameters
    ----------
    spec : list
        A list of specification elements. Typically, a bar element is formatted as:
        ["bar", start_coord, end_coord, {optional dictionary of parameters}].
    scale : float, optional
        The scaling factor applied to each coordinate. Default is 1.0.
    origin : tuple of int or float, optional
        The translation offset (x, y) applied after rotation. Default is (0, 0).
    rotation_deg : float, optional
        The rotation angle in degrees (about (0,0)) to apply. Default is 0.0.

    Returns
    -------
    list
        A new specification list with transformed bar coordinates. Non-bar elements are copied unchanged.

    Notes
    -----
    Angle-specific parameters (like 'angle_sweep' or 'angle') in the options dictionary are not altered.
    """
    transformed_spec = []
    for element in spec:
        if element[0] == "bar":
            start = element[1]
            end   = element[2]

            new_start = scale_rotate_translate_coord(
                start, scale=scale, rotation_deg=rotation_deg, origin=origin
            )
            new_end   = scale_rotate_translate_coord(
                end, scale=scale, rotation_deg=rotation_deg, origin=origin
            )

            if len(element) > 3:
                # Preserve the options dictionary if provided.
                transformed_element = ["bar", new_start, new_end, element[3]]
            else:
                transformed_element = ["bar", new_start, new_end]

            transformed_spec.append(transformed_element)
        else:
            # Copy non-bar elements (such as mechanism names) unchanged.
            transformed_spec.append(element)

    return transformed_spec

def combine_specs(*specs):
    """
    Combine multiple specification lists into one, removing any duplicate bars.

    For each provided specification:
      - If the item is a tuple (as might be returned by a reusable component), the first element
        (the transformed spec) is used.
      - Items that are None are skipped.
    After combining, duplicate bars (bars connecting the same two points, regardless of order)
    are removed from the final specification.

    Parameters
    ----------
    *specs : list or tuple
        A variable number of specification lists (or tuples containing a specification list) to combine.

    Returns
    -------
    list
        A single combined specification list with duplicate bars removed.
    """
    combined_spec = []
    for sp in specs:
        # If the item is a tuple, extract its first element.
        if isinstance(sp, tuple):
            sp = sp[0]
        # Only extend if the specification is not None.
        if sp is not None:
            combined_spec.extend(sp)
    combined_spec = remove_duplicate_bars(combined_spec)
    return combined_spec

def set_style_ground(spec, bar_list, decimal=3):
    """
    Mark specific bars in a specification as 'ground' by setting their style.

    This function searches for each bar specified in 'bar_list' within the spec.
    Matching is performed by rounding coordinates to the given precision (to account for float noise)
    and is independent of the order of the bar endpoints. When a match is found, the bar's
    options dictionary is updated (or created) to include {"style": "ground"}.

    Parameters
    ----------
    spec : list
        The specification list containing bar elements.
    bar_list : list of tuple
        A list of tuples, each representing a bar as ((start_x, start_y), (end_x, end_y)).
    decimal : int, optional
        The number of decimal places used when rounding coordinates for matching. Default is 3.

    Returns
    -------
    None

    Side Effects
    ------------
    The input specification list 'spec' is modified in-place.
    """
    for (bar_start, bar_end) in bar_list:
        bar_start = round_coord(bar_start, decimal)
        bar_end = round_coord(bar_end, decimal)

        for element in spec:
            if element[0] != "bar":
                continue

            s = round_coord(element[1], decimal)
            e = round_coord(element[2], decimal)

            if (s == bar_start and e == bar_end) or (s == bar_end and e == bar_start):
                if len(element) < 4 or not isinstance(element[3], dict):
                    element.append({"style": "ground"})
                else:
                    element[3]["style"] = "ground"

def set_angle_sweep(spec, bar_sweep_dict, decimal=3):
    """
    Set custom angle sweep ranges for specific bars in a specification.

    For each bar specified by a key in 'bar_sweep_dict', the function searches the specification
    for a matching bar (order-independent by rounding coordinates) and updates or adds the 'angle_sweep'
    parameter in its options dictionary.

    Parameters
    ----------
    spec : list
        The specification list containing bar elements.
    bar_sweep_dict : dict
        A dictionary where each key is a tuple of two coordinates ((start_x, start_y), (end_x, end_y))
        identifying a bar, and the corresponding value is a tuple (start_angle, end_angle, steps)
        defining the sweep range.
    decimal : int, optional
        The number of decimal places to round coordinates for matching. Default is 3.

    Returns
    -------
    None

    Examples
    --------
    >>> bar_sweep_dict = {
    ...     ((0.0, 0.0), (-0.25, 0.433)): (50, 50, 100),
    ...     ((0.0, 0.0), (2.0, 0.0)): (-25, 25, 50)
    ... }
    >>> set_angle_sweep(spec, bar_sweep_dict)
    """
    for (bar_start, bar_end), sweep_tuple in bar_sweep_dict.items():
        bar_start = round_coord(bar_start, decimal)
        bar_end = round_coord(bar_end, decimal)

        for element in spec:
            if element[0] != "bar":
                continue

            s = round_coord(element[1], decimal)
            e = round_coord(element[2], decimal)

            if (s == bar_start and e == bar_end) or (s == bar_end and e == bar_start):
                if len(element) < 4 or not isinstance(element[3], dict):
                    element.append({"angle_sweep": sweep_tuple})
                else:
                    element[3]["angle_sweep"] = sweep_tuple

def remove_duplicate_bars(spec, decimal=3):
    """
    Remove duplicate bars from a specification list.

    Two bars are considered duplicates if they connect the same pair of coordinates,
    regardless of the order of endpoints. Coordinates are rounded to the specified
    number of decimal places to mitigate floating-point precision issues.

    Parameters
    ----------
    spec : list
        The specification list containing bar elements.
    decimal : int, optional
        The number of decimal places for rounding coordinates during comparison. Default is 3.

    Returns
    -------
    list
        A new specification list with duplicate bars removed.
    """
    seen = set()
    new_spec = []
    for elem in spec:
        if elem[0] == "bar":
            # Round coordinates to avoid float precision issues.
            s = tuple(round(x, decimal) for x in elem[1])
            e = tuple(round(x, decimal) for x in elem[2])
            # Sort the coordinates to handle reversed order.
            ordered = tuple(sorted([s, e]))
            if ordered in seen:
                # Skip this bar if it has already been added.
                continue
            seen.add(ordered)
        new_spec.append(elem)
    return new_spec

def add_angle_joints_texts(mech, ani, ax):
    """
    Add text annotations for bar angles and joint names to an animation.

    This function creates two sets of annotations:
      - Angle annotations: For every bar connected to a followed joint, an annotation is created
        to display the current angle (in degrees) of that bar.
      - Joint name annotations: For joints that are flagged as followed or are connected to a followed
        joint, an annotation displaying the joint's name is added.

    The function then wraps the existing animation update function so that on every frame the
    annotations are updated with the latest positions and computed angles.

    Parameters
    ----------
    mech : Mechanism
        The mechanism object (typically created by a function such as create_linkage_from_spec)
        containing attributes such as 'joints' and 'vectors'.
    ani : Animation
        The animation object (for example, returned by mech.get_animation()).
    ax : matplotlib.axes.Axes
        The matplotlib Axes object used to display the animation.

    Returns
    -------
    Animation
        The updated animation object with the added text annotations.

    Notes
    -----
    The function modifies the internal animation function (_func) of the provided animation object.
    It uses a small offset (0.02) to position the text annotations so that they do not overlap with
    the animated elements.
    """
    # Create angle annotations for every bar connected to a followed joint.
    angle_texts = {}
    for joint in mech.joints:
        if not getattr(joint, "follow", False):
            continue
        for v in mech.vectors:
            # If the joint is one endpoint of the bar, determine the other endpoint.
            if v.joints[0] == joint:
                other = v.joints[1]
            elif v.joints[1] == joint:
                other = v.joints[0]
            else:
                continue
            # Create a text annotation near the bar.
            txt = ax.text(joint.x_pos or 0, joint.y_pos or 0, "",
                          fontsize=8, color="black")
            angle_texts[(joint.name, other.name)] = txt

    # Build the set of joints to annotate with their names.
    annotate_joints = set()
    # Add joints flagged as "follow".
    for joint in mech.joints:
        if getattr(joint, "follow", False):
            annotate_joints.add(joint)
    # For each vector, if one endpoint is in annotate_joints, add the other endpoint as well.
    for v in mech.vectors:
        if v.joints[0] in annotate_joints:
            annotate_joints.add(v.joints[1])
        if v.joints[1] in annotate_joints:
            annotate_joints.add(v.joints[0])
    # Create text annotations for each joint.
    joint_name_texts = {}
    for joint in annotate_joints:
        txt = ax.text(joint.x_pos or 0, joint.y_pos or 0, joint.name,
                      fontsize=8, color="blue")
        joint_name_texts[joint.name] = txt

    # Save a reference to the original animation function.
    orig_animate = ani._func

    # Define a new animate function that updates the annotations on each frame.
    def new_animate(frame):
        result = orig_animate(frame)
        offset = 0.02  # Small offset to avoid overlap of text with graphical elements.

        # Update angle text annotations.
        for (joint_name, other_name), txt in angle_texts.items():
            joint = next(j for j in mech.joints if j.name == joint_name)
            other = next(j for j in mech.joints if j.name == other_name)
            # Get current positions for both joints.
            if hasattr(joint, "x_positions") and joint.x_positions is not None:
                xj = joint.x_positions[frame]
                yj = joint.y_positions[frame]
            elif joint.x_pos is not None and joint.y_pos is not None:
                xj, yj = joint.x_pos, joint.y_pos
            else:
                continue  # Skip if positions are not defined.

            if hasattr(other, "x_positions") and other.x_positions is not None:
                xo = other.x_positions[frame]
                yo = other.y_positions[frame]
            elif other.x_pos is not None and other.y_pos is not None:
                xo, yo = other.x_pos, other.y_pos
            else:
                continue

            # Compute the angle (in degrees) of the bar from the current joint to the other joint.
            angle_rad = math.atan2(yo - yj, xo - xj)
            angle_deg = math.degrees(angle_rad)
            # Compute the midpoint of the bar.
            xm = (xj + xo) / 2
            ym = (yj + yo) / 2
            txt.set_position((xm + offset, ym + offset))
            txt.set_text(f"{angle_deg:.1f}°")

        # Update joint name annotations.
        for joint_name, txt in joint_name_texts.items():
            joint = next(j for j in mech.joints if j.name == joint_name)
            if hasattr(joint, "x_positions") and joint.x_positions is not None:
                xj = joint.x_positions[frame]
                yj = joint.y_positions[frame]
            elif joint.x_pos is not None and joint.y_pos is not None:
                xj, yj = joint.x_pos, joint.y_pos
            else:
                continue
            txt.set_position((xj + offset, yj + offset))
        return result + list(angle_texts.values()) + list(joint_name_texts.values())

    # Replace the original animation function with the new one.
    ani._func = new_animate
    return ani

