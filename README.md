# mechanismaf
A wrapper around the "mechanism" library for the "Algorithm Folding" lecture @ HPI

## Why mechanismaf?

**mechanismaf** is a high-level wrapper around the [mechanism](https://github.com/gabemorris12/mechanism) library designed for the "Algorithm Folding" lecture at HPI. Its primary goal is to simplify the creation, transformation, and animation of linkage mechanisms by abstracting away the low-level complexities of the underlying library.

The underlying **mechanism** library is very powerful but also very complicated. For example, when creating a linkage directly with **mechanism**, you must manually:
- Define each joint and bar (vector).
- Set up the loop equations for solving the unknown angles.
- Specify initial guesses, sweep angles, and other details.
- Build and manage the animation.

**mechanismaf** provides a more accessible API that allows you to define your mechanism using simple specifications (lists of bars with coordinates and optional properties) while automatically handling:
- Joint and vector creation.
- Grounding, sweep configuration, and loop detection.
- Geometric transformations (scaling, rotation, and translation).
- Animation enhancements (injecting bar angles and joint names).

## Installation

Install **mechanismaf** using pip:

```bash
pip install mechanismaf
```

## What mechanismaf Does

- **Simplifies Linkage Creation:** Define mechanisms by listing bars and their properties instead of manually creating joints, vectors, loops, and initial guesses.
- **Reusable Components:** Easily combine and transform mechanism specifications with functions such as transform_spec and combine_specs.
- **Enhanced Animations:** Automatically inject text annotations (bar angles and joint names) into your mechanism animations using add_angle_joints_texts.
- **Automatic Parameter Management:** Functions like set_style_ground and set_angle_sweep let you adjust properties such as fixed (ground) angles and sweep ranges without dealing with the underlying low-level API.

## Exposed Functions
The package exposes a number of functions that make working with mechanisms more straightforward:

- `create_linkage_from_spec(spec, follow_points=None, log_level=logging.INFO, log_file=None)`: Creates and solves a linkage mechanism from a simplified specification list. This function automatically sets up joints, vectors, loops, and iterations.
- `transform_spec(spec, scale=1.0, origin=(0, 0), rotation_deg=0.0)`: Transforms a mechanism specification by applying scaling, rotation, and translation to all bar coordinates.
- `combine_specs(*specs)`: Combines multiple mechanism specifications into a single list, removing duplicate bars.
- `set_style_ground(spec, bar_list, decimal=3)`: Marks specific bars as ground (fixed) in the specification by setting their style attribute.
- `set_angle_sweep(spec, bar_sweep_dict, decimal=3)`: Configures custom angle sweep ranges for specified bars in the specification.
- `add_angle_joints_texts(mech, ani, ax)`: Injects annotations for bar angles and joint names into the animation of a mechanism.

Additional helper functions such as `round_coord` and `transform_follow_points` further ease the process of working with coordinates and transformations.

## Examples
### Creating a Peaucellier–Lipkin Linkage Using the Bare mechanism Library
The following example shows the amount of work needed when using the underlying mechanism library directly:

```python
#!/usr/bin/env python3

import numpy as np
import matplotlib.pyplot as plt
from mechanism import *

# Create Joints
O, A, B, C, D, E = get_joints("O A B C D E")
C.follow, D.follow, E.follow = True, True, True

# Define Bars (Vectors)
OA = Vector((O, A), r=1, theta=0, style='ground')  # ground
AB = Vector((A, B), r=1)                           # input
BC = Vector((B, C), r=np.sqrt(2))
CD = Vector((C, D), r=np.sqrt(2))
DE = Vector((D, E), r=np.sqrt(2))
EB = Vector((E, B), r=np.sqrt(2))
OC = Vector((O, C), r=np.sqrt(10))  # pivot about O
OE = Vector((O, E), r=np.sqrt(10))  # pivot about O

# Define the loop equations (6 unknown angles, 3 loops)
def loops(x, input_angle):
    """
    x = [θ_BC, θ_CD, θ_DE, θ_EB, θ_OC, θ_OE]
    input_angle = angle for AB (our driven link)
    """
    theta_bc, theta_cd, theta_de, theta_eb, theta_oc, theta_oe = x

    temp = np.zeros((3, 2))

    # Loop1: O->A->B->C->O
    temp[0] = OA() + AB(input_angle) + BC(theta_bc) - OC(theta_oc)

    # Loop2: O->C->D->E->O
    temp[1] = OC(theta_oc) + CD(theta_cd) + DE(theta_de) - OE(theta_oe)

    # Loop3: B->C->D->E->B
    temp[2] = BC(theta_bc) + CD(theta_cd) + DE(theta_de) + EB(theta_eb)

    return temp.flatten()

# Build "Up-and-Down" Angles for sweeping the mechanism.
angles_up   = np.linspace(-25, 25, 50)   # 50 points
angles_down = np.linspace(25, -25, 50)    # 50 points
angles_full = np.concatenate([angles_up, angles_down[1:]])
angles_rad = np.deg2rad(angles_full)

# Initial guess for the 6 unknown angles
guess0 = np.deg2rad([45, -45, -135, 135, 18, -18])

# Construct the Mechanism
mechanism = Mechanism(
    vectors=(OA, AB, BC, CD, DE, EB, OC, OE),
    origin=O,
    loops=loops,
    pos=angles_rad,
    guess=(guess0,)
)

# Solve and animate
mechanism.iterate()
ani, fig, ax = mechanism.get_animation(cushion=1.0)
ax.set_title("Peaucellier–Lipkin linkage")
plt.show()
```

### Creating a Peaucellier–Lipkin Linkage Using mechanismaf
With **mechanismaf**, creating the same mechanism is much simpler. You simply define a specification that describes the bars and their properties:

```python
#!/usr/bin/env python3

from mechanismaf import create_linkage_from_spec
import matplotlib.pyplot as plt

if __name__ == "__main__":
    spec = [
        ["bar", (0.0, 0.0), (2, 1)],
        ["bar", (0.0, 0.0), (2, -1)],
        ["bar", (2, 1), (1, 0)],
        ["bar", (1, 0), (2, -1)],
        ["bar", (2, -1), (3, 0)],
        ["bar", (3, 0), (2, 1)],
        ["bar", (0, 0), (0.5, 0.0), {"style": "ground", "angle": 0}],
        ["bar", (0.5, 0.0), (1.0, 0.0), {"angle_sweep": (-25, 25, 50)}],
    ]

    follow_points = [(2, 1), (2, -1), (3, 0)]
    mechanism = create_linkage_from_spec(spec, follow_points=follow_points)
    ani, fig, ax = mechanism.get_animation(cushion=1.0)
    ax.set_title("Peaucellier–Lipkin linkage")
    plt.show()
```

### Further Examples

#### Create & Use Resuable Components
This example will show you how to create reusable components and how to use them. Let's define a simple rectangle:

```python
from mechanismaf import (
    create_linkage_from_spec,
)
import matplotlib.pyplot as plt

spec = [
        ["bar", (0, 0), (0, 1), {"style": "ground"}],
        ["bar", (0, 1), (1, 1), {"angle_sweep": (20, -20, 20)}],
        ["bar", (1, 1), (1, 0)],
        ["bar", (1, 0), (0, 0)],
    ]

mech = create_linkage_from_spec(spec)
ani, fig, ax = mech.get_animation()
ax.set_title("Simple rectangle")
plt.show()
```

To make this rectangle reusable, all we need to do is to create a function that defines our bars and calls the functions to tranform the spec. Please note that you should remove the ground and angle_sweep bar and set their role later:

```python
from mechanismaf import (
    set_style_ground,
    set_angle_sweep,
    transform_spec,
    transform_follow_points
)

def create_rectangle(
    scale=1.0,
    origin=(0, 0),
    rotation_deg=0.0,
    bars_to_ground=None,
    sweep_bars_dict=None,
    base_follow_points=None
):
    # Bare-bones spec (no ground, no angle_sweep)
    base_spec = [
        ["bar", (0, 0), (0, 1)],
        ["bar", (0, 1), (1, 1)],
        ["bar", (1, 1), (1, 0)],
        ["bar", (1, 0), (0, 0)],
    ]

    # Optionally set bars as ground
    if bars_to_ground:
        set_style_ground(base_spec, bars_to_ground)

    # Optionally set bars to angle_sweep
    if sweep_bars_dict:
        set_angle_sweep(base_spec, sweep_bars_dict)

    # Transform the geometry:
    transformed_spec = transform_spec(base_spec, scale=scale, origin=origin, rotation_deg=rotation_deg)
    
    # Transform follow points (if provided)
    if base_follow_points:
        transformed_follow = transform_follow_points(base_follow_points, scale=scale, 
                                                       rotation_deg=rotation_deg, origin=origin)
    else:
        transformed_follow = None

    return transformed_spec, transformed_follow
```

We can use this now by adding this snippet that actually creates the spec:

```python
from mechanismaf import (
    create_linkage_from_spec,
    add_angle_joints_texts
)
import matplotlib.pyplot as plt

bars_ground1 = [((0.0, 0.0), (0.0, 1.0))]
bars_sweep_dict = {
    ((0.0, 1.0), (1, 1)): (-30, 30, 30),
}
base_follow_points1 = [(1, 1)]

rectangle, follow_points1 = create_rectangle(
    scale=2.0,
    rotation_deg=60,
    bars_to_ground=bars_ground1,
    sweep_bars_dict=bars_sweep_dict,
    base_follow_points=base_follow_points1
)

mech = create_linkage_from_spec(rectangle, follow_points=follow_points1)
ani, fig, ax = mech.get_animation()
ax.set_title("Reusable rectangle")
add_angle_joints_texts(mech, ani, ax)
ani
plt.show()
```

This code now calls the function to create the rectangle, scales it, rotates it etc. We can also create a second rectangle on the other side as well:

```python
from mechanismaf import (
    combine_specs,
    create_linkage_from_spec,
    add_angle_joints_texts
)
import matplotlib.pyplot as plt

bars_ground1 = [((0.0, 0.0), (0.0, 1.0))]
bars_sweep_dict = {
    ((0.0, 1.0), (1, 1)): (-30, 30, 30),
}
base_follow_points1 = [(1, 1)]

rectangle, follow_points1 = create_rectangle(
    scale=2.0,
    rotation_deg=60,
    bars_to_ground=bars_ground1,
    sweep_bars_dict=bars_sweep_dict,
    base_follow_points=base_follow_points1
)

rectangle2, follow_points2 = create_rectangle(
    scale=2.0,
    rotation_deg=-120,
    bars_to_ground=bars_ground1,
    sweep_bars_dict=bars_sweep_dict,
    base_follow_points=base_follow_points1
)

spec=combine_specs(rectangle, rectangle2)
follow_points=follow_points1 + follow_points2
mech = create_linkage_from_spec(spec, follow_points=follow_points)
ani, fig, ax = mech.get_animation()
ax.set_title("Reusable contra-parallelogram")
add_angle_joints_texts(mech, ani, ax)
ani
plt.show()
```

We now use the `combine_spec` function to combine the two rectangles into one spec to pass it to **mechanismaf**.

### What You Don't Need to Do with mechanismaf
When using **mechanismaf**:

- **No Manual Joint/Vector Creation:** You do not need to create joints and vectors manually.
- **No Loop Equations:** There is no need to write your own loop equations; the library automatically detects loops and sets up the equations.
- **No Initial Guess Management:** The mechanism’s unknown angles and sweep parameters are automatically handled.
- **Enhanced Transformations:** Functions for transforming and combining specifications allow you to work at a higher level of abstraction.

Extra Features

- **Reusable Components:** Easily transform and merge specifications using functions like transform_spec and combine_specs.
- **Animation Annotations:** Automatically inject angle and joint annotations into your mechanism animations via add_angle_joints_texts.
- **Parameter Flexibility:** Quickly set or update bar properties (such as ground style or sweep ranges) without delving into the underlying mechanism details.

## Additional Information
For more details, visit the [PyPI project page](https://pypi.org/project/mechanismaf/).

**mechanismaf** was developed to enable researchers, educators, and students to experiment with and animate linkage mechanisms with minimal boilerplate code. By wrapping the complexities of the underlying mechanism library, it lets you focus on design and analysis rather than implementation details. **mechanismaf** has been created as part of the HCI project seminar at HPI.

## License
**mechanismaf** is licensed under the **MIT** license.

## Contributing
Contributions, feature requests, and bug reports are welcome! Please open an issue or submit a pull request on the GitHub repository.

## Acknowledgements
Special thanks to the developers of the underlying mechanism library and to the HPI community for their support.

