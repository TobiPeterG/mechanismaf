#!/usr/bin/env python3
import math

def round_coord(coord, decimal=3):
    """Round a coordinate tuple to a fixed number of decimal places."""
    return tuple(round(float(x), decimal) for x in coord)

def transform_follow_points(points, scale=1.0, rotation_deg=0.0, origin=(0, 0)):
    """
    Given a list of follow points (each a coordinate tuple),
    return a new list where each point is transformed (scaled, rotated, and translated)
    with the same parameters as used for the geometry.
    """
    return [scale_rotate_translate_coord(pt, scale=scale, rotation_deg=rotation_deg, origin=origin) 
            for pt in points]

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

    (Does NOT automatically change angle_sweep or angle in the dict.)
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
                # Keep the dictionary if any
                transformed_element = ["bar", new_start, new_end, element[3]]
            else:
                transformed_element = ["bar", new_start, new_end]

            transformed_spec.append(transformed_element)
        else:
            # Copy non-bar elements (like ["name", ...]) as-is
            transformed_spec.append(element)

    return transformed_spec

def combine_specs(*specs):
    """
    Combine multiple specs into a single list.
    If an item is a tuple (as returned by your reusable component),
    take its first element (the transformed spec).
    Skip any items that are None.
    """
    combined_spec = []
    for sp in specs:
        # If the item is a tuple, take its first element.
        if isinstance(sp, tuple):
            sp = sp[0]
        # Only extend if sp is not None
        if sp is not None:
            combined_spec.extend(sp)
    combined_spec = remove_duplicate_bars(combined_spec)
    return combined_spec


def set_style_ground(spec, bar_list, decimal=3):
    """
    For each (start, end) in bar_list, find the matching bar in `spec` (either direction),
    and set `style='ground'` in its dictionary.
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
    Set different angle_sweep ranges for specific bars in `spec`.

    `bar_sweep_dict` should be a dictionary where:
    - The key is a tuple ((start_x, start_y), (end_x, end_y))
    - The value is the sweep range tuple (start_angle, end_angle, steps)

    Example:
        bar_sweep_dict = {
            ((0.0, 0.0), (-0.25, 0.433)): (50, 50, 100),  # Specific range for this bar
            ((0.0, 0.0), (2.0, 0.0)): (-25, 25, 50)       # Another range for this one
        }
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
    seen = set()
    new_spec = []
    for elem in spec:
        if elem[0] == "bar":
            # Round to avoid float noise
            s = tuple(round(x, decimal) for x in elem[1])
            e = tuple(round(x, decimal) for x in elem[2])
            # Sort to handle reversed bar
            ordered = tuple(sorted([s,e]))
            if ordered in seen:
                # Skip repeated bar
                continue
            seen.add(ordered)
        new_spec.append(elem)
    return new_spec

def add_angle_joints_texts(mech, ani, ax):
    """
    Adds text annotations for bar angles and joint names to an existing animation.

    This function creates two sets of annotations:
      - Angle annotations for each bar connected to a followed joint.
      - Joint name annotations for all joints that are either followed or connected to a followed joint.

    It then wraps the animation function to update these texts on every frame.

    Parameters:
      mech: The mechanism object (as returned by create_linkage_from_spec).
      ani: The animation object (e.g., returned by mech.get_animation()).
      ax: The matplotlib Axes object used in the animation.
    """
    # Create angle annotations for every bar connected to a followed joint.
    angle_texts = {}
    for joint in mech.joints:
        if not getattr(joint, "follow", False):
            continue
        for v in mech.vectors:
            # If the joint is one end of the bar, then get the other end.
            if v.joints[0] == joint:
                other = v.joints[1]
            elif v.joints[1] == joint:
                other = v.joints[0]
            else:
                continue
            # Create a text annotation near the bar.
            txt = ax.text(joint.x_pos or 0, joint.y_pos or 0, "",
                          fontsize=8, color="red")
            angle_texts[(joint.name, other.name)] = txt

    # Build the set of joints to annotate with joint names.
    annotate_joints = set()
    # Add joints flagged as "follow".
    for joint in mech.joints:
        if getattr(joint, "follow", False):
            annotate_joints.add(joint)
    # For every vector, if one endpoint is in annotate_joints, add the other.
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

    # Define the new animate function.
    def new_animate(frame):
        result = orig_animate(frame)
        offset = 0.02  # small offset to avoid overlap

        # Update angle text annotations.
        for (joint_name, other_name), txt in angle_texts.items():
            joint = next(j for j in mech.joints if j.name == joint_name)
            other = next(j for j in mech.joints if j.name == other_name)
            # Get current positions for both joints:
            if hasattr(joint, "x_positions") and joint.x_positions is not None:
                xj = joint.x_positions[frame]
                yj = joint.y_positions[frame]
            elif joint.x_pos is not None and joint.y_pos is not None:
                xj, yj = joint.x_pos, joint.y_pos
            else:
                continue  # skip if positions not defined

            if hasattr(other, "x_positions") and other.x_positions is not None:
                xo = other.x_positions[frame]
                yo = other.y_positions[frame]
            elif other.x_pos is not None and other.y_pos is not None:
                xo, yo = other.x_pos, other.y_pos
            else:
                continue

            # Compute the angle (in degrees) of the bar (from joint to other)
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

    # Replace the animation function with the new one.
    ani._func = new_animate
    return ani
