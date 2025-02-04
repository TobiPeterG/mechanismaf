#!/usr/bin/env python3

import numpy as np
from mechanism import Mechanism, Vector, Joint
import networkx as nx
import math
import logging

def create_linkage_from_spec(spec, follow_points=None, log_level=logging.INFO, log_file=None):
    """
    Creates a linkage mechanism from a specification list, distinguishing between:
      - Bars that are truly user-fixed (angle automatically calculated from coordinates)
      - Bars that have unknown angles
      - Bars that sweep (angle_sweep)
    Supports multiple sweep vectors.

    Parameters:
    - spec: List of specifications defining the mechanism.
    - follow_points: Optional list of points to follow (those joints become .follow=True).
    - log_level: Logging level (e.g., logging.DEBUG, logging.INFO).
    - log_file: Optional path to a file to write logs.
    """

    # Configure the logger
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)

    # Prevent adding multiple handlers if the function is called multiple times
    if not logger.handlers:
        # Create console handler with the specified log level
        ch = logging.StreamHandler()
        ch.setLevel(log_level)

        # Create formatter and add it to the handler
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        ch.setFormatter(formatter)

        # Add the console handler to the logger
        logger.addHandler(ch)

        # If a log_file is specified, add a FileHandler
        if log_file:
            fh = logging.FileHandler(log_file)
            fh.setLevel(log_level)
            fh.setFormatter(formatter)
            logger.addHandler(fh)

    def assign_joint_names(joint_coords):
        joint_names = {}
        for idx, coord in enumerate(joint_coords):
            joint_names[coord] = f"J{idx}"
        return joint_names

    def find_unique_joints(spec, decimal=3):
        coords = set()
        for element in spec:
            if element[0] == "bar":
                c1 = round_coord(element[1], decimal)
                c2 = round_coord(element[2], decimal)
                coords.add(c1)
                coords.add(c2)
        return list(coords)

    def identify_ground_joints(spec, decimal=3):
        g_joints = set()
        for element in spec:
            if element[0] == "bar" and len(element) > 3:
                if isinstance(element[3], dict) and element[3].get('style', '').lower() == 'ground':
                    c1 = round_coord(element[1], decimal)
                    c2 = round_coord(element[2], decimal)
                    g_joints.add(c1)
                    g_joints.add(c2)
        return g_joints

    def round_coord(coord, decimal=3):
        return tuple(round(float(x), decimal) for x in coord)

    def deg_to_rad(deg):
        return deg * np.pi / 180.0

    # -------------------------------------------------------------------------
    # A custom loop_equations that handles multiple sweep vectors
    # Each sweep vector has its own sweep_angle
    # -------------------------------------------------------------------------
    def generate_loop_equations(vectors, loops, sweep_vectors, natural_sweep_angles):
        def loop_equations(x, sweep_angles):
            logger.debug("--- loop_equations called ---")
            # sweep_angles is a list matching sweep_vectors

            angle_dict = {}
            x_idx = 0

            # 1) Assign angles to unknown bars and sweep vectors
            for vec in vectors:
                if vec in sweep_vectors:
                    # Assign the corresponding sweep angle
                    idx = sweep_vectors.index(vec)
                    angle_dict[vec] = sweep_angles[idx]
                elif getattr(vec, "_is_user_fixed_angle", False):
                    # Fixed angle
                    angle_dict[vec] = vec.natural_angle
                else:
                    # Unknown angle
                    angle_dict[vec] = x[x_idx]
                    x_idx += 1

            # 2) For each loop, sum up
            eqns = []
            loop_count = 0
            for loop in loops:
                loop_count += 1
                sum_x = 0
                sum_y = 0
                logger.debug(f"  Loop {loop_count} debug:")

                for vec, direction in loop:
                    if getattr(vec, "_is_user_fixed_angle", False):
                        logger.debug(f"    {vec} => user-fixed => calling vec() no args.")
                        vxy = vec()  # Fixed angle
                    elif vec in sweep_vectors:
                        ang_deg = np.degrees(angle_dict[vec])
                        logger.debug(f"    {vec} => sweep => calling vec({ang_deg:.2f} deg).")
                        vxy = vec(angle_dict[vec])
                    else:
                        ang_deg = np.degrees(angle_dict[vec])
                        logger.debug(f"    {vec} => unknown => calling vec({ang_deg:.2f} deg).")
                        vxy = vec(angle_dict[vec])

                    sum_x += direction * vxy[0]
                    sum_y += direction * vxy[1]

                eqns.extend([sum_x, sum_y])
            return np.array(eqns)

        return loop_equations

    # Step 1: Possibly get mechanism name
    linkage_name = "Unnamed"
    for element in spec:
        if element[0] == "name":
            linkage_name = element[1]
            break

    # Step 2: Build joint mappings
    unique_joints = find_unique_joints(spec)
    joint_names = assign_joint_names(unique_joints)

    logger.info("Joint Names Mapping:")
    for c, n in joint_names.items():
        logger.info(f"  {n}: {c}")

    # Step 3: Create Joint objects (without fixing any joint)
    joints = {}
    for coord, name in joint_names.items():
        j = Joint(name=name)
        joints[name] = j
        # Do not fix any joint here

    # Step 4: Create a mapping from joint names to coordinates
    joint_coords = {name: coord for coord, name in joint_names.items()}

    # Step 5: Identify ground joints
    ground_joints = identify_ground_joints(spec)
    if follow_points is not None:
        follow_joints = set(round_coord(pt) for pt in follow_points)
    else:
        follow_joints = ground_joints

    logger.info("Follow Joints:")
    for c in follow_joints:
        logger.info(f"  {c}")

    # Step 6: Select origin joint from ground joints
    if not ground_joints:
        raise ValueError("No ground joints found in the specification.")

    origin_coord = min(ground_joints, key=lambda c: (c[0], c[1]))
    origin_joint_name = joint_names.get(origin_coord)

    if not origin_joint_name:
        raise ValueError(f"Origin joint at {origin_coord} not found.")

    origin_joint = joints.get(origin_joint_name)
    if not origin_joint:
        raise ValueError(f"Origin joint {origin_joint_name} not found.")

    # Step 7: Fix the origin joint's position
    origin_joint._fix_position(*origin_coord)

    # Step 8: Mark follow=True for follow_joints
    for coord, jname in joint_names.items():
        if coord in follow_joints:
            joints[jname].follow = True

    # Step 9: Create Vector objects
    vectors = []
    sweep_vectors = []
    natural_sweep_angles = []
    for element in spec:
        if element[0] == "bar":
            start_coord = round_coord(element[1])
            end_coord   = round_coord(element[2])
            style = angle_deg = angle_sweep = None

            if len(element) > 3 and isinstance(element[3], dict):
                style       = element[3].get('style', None)
                angle_deg   = element[3].get('angle', None)
                angle_sweep = element[3].get('angle_sweep', None)

            start_joint = joints[joint_names[start_coord]]
            end_joint   = joints[joint_names[end_coord]]
            r = np.hypot(end_coord[0] - start_coord[0], end_coord[1] - start_coord[1])

            # Create the vector
            if style == 'ground':
                # Treat as fixed angle
                natural_angle = np.arctan2(end_coord[1] - start_coord[1], end_coord[0] - start_coord[0])
                vec = Vector(joints=(start_joint, end_joint), r=r, theta=natural_angle, style=style)
                vec._is_user_fixed_angle = True
                vec.natural_angle = natural_angle
                vectors.append(vec)

            elif angle_sweep is not None:
                # Sweep vector => unknown angle each iteration
                vec = Vector(joints=(start_joint, end_joint), r=r, style=style)
                vec._is_user_fixed_angle = False
                # Calculate and store natural angle
                natural_angle = np.arctan2(end_coord[1] - start_coord[1], end_coord[0] - start_coord[0])
                vec.natural_angle = natural_angle
                sweep_vectors.append(vec)
                vectors.append(vec)

            elif angle_deg is not None:
                # Fixed angle (if any other fixed angles are specified)
                natural_angle = np.arctan2(end_coord[1] - start_coord[1], end_coord[0] - start_coord[0])
                vec = Vector(joints=(start_joint, end_joint), r=r, theta=natural_angle, style=style)
                vec._is_user_fixed_angle = True
                vec.natural_angle = natural_angle
                vectors.append(vec)

            else:
                # Unknown angle => set _is_user_fixed_angle=False
                vec = Vector(joints=(start_joint, end_joint), r=r, style=style)
                vec._is_user_fixed_angle = False
                vectors.append(vec)

    logger.info("Vectors Created:")
    for vec in vectors:
        if vec in sweep_vectors:
            status = "Sweep"
        elif getattr(vec, "_is_user_fixed_angle", False):
            status = "Fixed"
        else:
            status = "Unknown"
        # Retrieve rounded joint coordinates
        start_jname = vec.joints[0].name
        end_jname = vec.joints[1].name
        try:
            start_coord = joint_coords[start_jname]
            end_coord = joint_coords[end_jname]
        except KeyError as e:
            raise KeyError(f"Joint name '{e.args[0]}' not found in joint_coords.")

        logger.info(f"  {start_jname} ({start_coord}) -> {end_jname} ({end_coord}) ({status})")

    # Step 10: Collect sweep parameters for each sweep vector
    sweep_vectors_params = []
    for vec in sweep_vectors:
        sweep_params = None
        for element in spec:
            if element[0] == "bar":
                if len(element) > 3 and isinstance(element[3], dict):
                    if 'angle_sweep' in element[3]:
                        # Match the sweep vector by checking if the vector's joints match
                        sweep_start = round_coord(element[1])
                        sweep_end = round_coord(element[2])
                        vec_start = joint_coords[vec.joints[0].name]
                        vec_end = joint_coords[vec.joints[1].name]
                        if (
                            (sweep_start == vec_start and sweep_end == vec_end) or
                            (sweep_start == vec_end   and sweep_end == vec_start)
                        ):
                            sweep_params = element[3]['angle_sweep']
                            logger.info(
                                f"Assigning sweep_params {sweep_params} to vector "
                                f"{vec.joints[0].name} -> {vec.joints[1].name}"
                            )
                            break
        if sweep_params is None:
            sweep_params = (-25, 25, 50)  # Default sweep if not specified
            logger.info(f"No specific sweep_params found for vector {vec.joints[0].name} -> {vec.joints[1].name}. "
                        f"Using default {sweep_params}.")
        sweep_vectors_params.append(sweep_params)

    # Ensure that we have sweep parameters for all sweep vectors
    if len(sweep_vectors) != len(sweep_vectors_params):
        raise ValueError("Mismatch between number of sweep vectors and sweep parameters.")

    # Step 11: Extract angle sweep info for each sweep vector
    sweep_angles_list = []
    for idx, sweep_vector in enumerate(sweep_vectors):
        sweep_params = sweep_vectors_params[idx]
        sweep_start_deg, sweep_end_deg, sweep_num = sweep_params

        # Calculate sweep angles in radians
        sweep_angles_deg = np.linspace(sweep_start_deg, sweep_end_deg, sweep_num)
        sweep_angles_rad = deg_to_rad(sweep_angles_deg) + sweep_vector.natural_angle

        # Sweep back (if desired to 'oscillate')
        sweep_angles_rev_deg = np.linspace(sweep_end_deg, sweep_start_deg, sweep_num)[1:]
        sweep_angles_rev_rad = deg_to_rad(sweep_angles_rev_deg) + sweep_vector.natural_angle

        # Combine up and down sweep
        angles_full_rad = np.concatenate([sweep_angles_rad, sweep_angles_rev_rad])

        sweep_angles_list.append(angles_full_rad)

    # Step 12: Build sweep_angles_stepwise
    # Ensure all sweep vectors have the same number of sweep angles
    min_steps = min(len(sweep_angles) for sweep_angles in sweep_angles_list)
    sweep_angles_stepwise = [
        [sweep_angles_list[j][i] for j in range(len(sweep_vectors))]
        for i in range(min_steps)
    ]

    # Step 13: Build initial guess for unknown angles (ignore user-fixed or sweep)
    unknown_vectors = [
        v for v in vectors
        if (not getattr(v, "_is_user_fixed_angle", False)) and (v not in sweep_vectors)
    ]
    if not unknown_vectors and not sweep_vectors:
        raise ValueError("No unknown angles found. (All bars fixed + no sweep vectors => no DOF?)")

    guess_list = []
    for vec in unknown_vectors:
        s = None
        e = None
        for el in spec:
            if el[0] == "bar":
                c1 = round_coord(el[1])
                c2 = round_coord(el[2])
                if (joint_names[c1] == vec.joints[0].name and
                        joint_names[c2] == vec.joints[1].name):
                    s, e = c1, c2
                    break
                elif (joint_names[c2] == vec.joints[0].name and
                      joint_names[c1] == vec.joints[1].name):
                    s, e = c2, c1
                    break
        if s and e:
            dx = e[0] - s[0]
            dy = e[1] - s[1]
            guess_list.append(np.arctan2(dy, dx))
        else:
            guess_list.append(0.0)

    guess_initial = np.array(guess_list)
    logger.debug("Initial Guess (radians): %s", guess_initial)

    # Step 14: Identify loops with networkx
    G = nx.Graph()
    for vec in vectors:
        j1 = vec.joints[0].name
        j2 = vec.joints[1].name
        G.add_edge(j1, j2)

    cycles = nx.cycle_basis(G)
    if not cycles:
        raise ValueError("No loops found in the mechanism.")

    logger.debug(f"Total Loops Found: {len(cycles)}")
    for i, cyc in enumerate(cycles, 1):
        logger.debug(f"  Loop {i}: {cyc}")

    # Step 15: Convert loops -> (vector, direction)
    loop_vectors = []
    for cyc in cycles:
        cyc_closed = cyc + [cyc[0]]
        vloop = []
        for i in range(len(cyc)):
            A = cyc_closed[i]
            B = cyc_closed[i+1]
            for vec in vectors:
                nameA = vec.joints[0].name
                nameB = vec.joints[1].name
                if nameA == A and nameB == B:
                    vloop.append((vec, 1))
                    break
                elif nameB == A and nameA == B:
                    vloop.append((vec, -1))
                    break
            else:
                raise ValueError(f"No vector found connecting {A} to {B}!")
        loop_vectors.append(vloop)

    logger.debug("Loop Vectors:")
    for i, vloop in enumerate(loop_vectors, start=1):
        logger.debug(f"  Loop {i}:")
        for vec, direction in vloop:
            dirstr = "Fwd" if direction == 1 else "Rev"
            logger.debug(f"    {vec.joints[0].name}->{vec.joints[1].name} {dirstr}")

    # Step 16: Build the loop function
    loop_func = generate_loop_equations(
        vectors,
        loop_vectors,
        sweep_vectors,
        [vec.natural_angle for vec in sweep_vectors]
    )

    # Step 17: Create Mechanism using the selected origin joint
    mech = Mechanism(
        vectors=vectors,
        origin=origin_joint,
        loops=loop_func,
        pos=np.array(sweep_angles_stepwise) if sweep_vectors else None,  # If no sweep_vectors, pos=None
        guess=(guess_initial,)
    )

    # Step 18: Iterate the mechanism
    try:
        if sweep_vectors:
            # If we have any sweep vectors, they define the .pos array
            mech.iterate()
        else:
            # Otherwise, we have a single solve (if everything is fixed except unknowns).
            # We still use .iterate() with a single step if you prefer, or just .calculate().
            # For consistency, let's do iterate() in case there's more code that depends on iteration.
            # We'll shape our .pos as shape[0]==1
            if len(guess_initial) == 0:
                # No unknowns at all -> just fix positions once
                mech.pos = np.array([0.0])  # dummy
                mech.iterate()
            else:
                # We still want to solve once
                mech.pos = np.array([0.0])  # dummy to let iterate do 1 step
                mech.iterate()

    except Exception as e:
        raise RuntimeError(f"Failed to iterate the mechanism: {e}")

    # ---------------------------------------------------------------------
    # (NEW) Print angles at each iteration for the followed joints
    # ---------------------------------------------------------------------
    _print_followed_joint_angles(mech, logger)

    return mech


def _print_followed_joint_angles(mech, logger):
    """
    For each iteration (frame) in the Mechanism, for each joint that is flagged as .follow == True,
    compute and print the angle (relative to the X-axis) of each bar connected to that joint,
    along with the coordinates of the joint and the connected joint.
    
    The angle is computed from the followed joint's position to the position of the other joint of the vector.
    """
    # If mech.pos is a scalar or None, assume there is one frame.
    if not isinstance(mech.pos, np.ndarray) or mech.pos.ndim == 0:
        frames_count = 1
    else:
        frames_count = len(mech.pos)

    # Select joints that are flagged to be followed.
    followed_joints = [j for j in mech.joints if j.follow]

    for i in range(frames_count):
        for joint in followed_joints:
            # Determine the current position of the followed joint.
            if frames_count > 1:
                x_j = joint.x_positions[i]
                y_j = joint.y_positions[i]
            else:
                x_j, y_j = joint.x_pos, joint.y_pos

            # Loop over all vectors and check if this joint is an endpoint.
            # For each such vector, compute the angle (in degrees) of the bar with respect to the X-axis.
            for v in mech.vectors:
                # Check if this vector is connected to the current joint.
                # We want to compute the angle from 'joint' to the other joint.
                if v.joints[0] == joint:
                    other = v.joints[1]
                elif v.joints[1] == joint:
                    other = v.joints[0]
                else:
                    continue  # This vector is not connected to the current joint.

                # Get the position of the "other" joint.
                if frames_count > 1:
                    x_o = other.x_positions[i]
                    y_o = other.y_positions[i]
                else:
                    x_o, y_o = other.x_pos, other.y_pos

                # Compute the vector from the followed joint to the other joint.
                dx = x_o - x_j
                dy = y_o - y_j
                # Use arctan2 to get the angle relative to the positive X-axis.
                angle_rad = math.atan2(dy, dx)
                angle_deg = math.degrees(angle_rad)

                logger.info(
                    f"Iteration {i}, Joint {joint.name} at ({x_j:.3f}, {y_j:.3f}): "
                    f"bar to {other.name} at ({x_o:.3f}, {y_o:.3f}) has angle {angle_deg:.3f} deg relative to the X-axis"
                )
