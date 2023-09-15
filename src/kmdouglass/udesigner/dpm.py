"""Design equations for a diffraction phase microscope.

This module contains the equations used to design a diffraction phase microscope. The equations are
based on [1] with a few additions.

References
----------
[1] Bhaduri, et al., "Diffraction phase microscopy: principles and applications in materials and
life sciences," Advances in Optics and Photonics 6, 57-119, (2014). https://doi.org/10.1364/AOP.6.000057

"""

import base64
import io
import json
from pathlib import Path
from typing import Any, Optional, TypedDict

from jinja2 import Environment, PackageLoader
import matplotlib.pyplot as plt

from kmdouglass.udesigner import Result, Units


Inputs = TypedDict(
    "Inputs",
    {
        "objective.magnification": float,
        "objective.numerical_aperture": float,
        "camera.pixel_size": float,
        "camera.pixel_size.units": Units,
        "camera.horizontal_number_of_pixels": int,
        "camera.vertical_number_of_pixels": int,
        "light_source.wavelength": float,
        "light_source.wavelength.units": Units,
        "grating.period": float,
        "grating.period.units": Units,
        "lens_1.focal_length": float,
        "lens_1.focal_length.units": Units,
        "lens_1.clear_aperture": float,
        "lens_1.clear_aperture.units": Units,
        "lens_2.focal_length": float,
        "lens_2.focal_length.units": Units,
        "lens_2.clear_aperture": float,
        "lens_2.clear_aperture.units": Units,
        "pinhole.diameter": float,
        "pinhole.diameter.units": Units,
        "misc.central_lobe_size_factor": float,
    }
)


DEFAULTS = {
    "objective.magnification": 20,
    "objective.numerical_aperture": 0.4,
    "camera.pixel_size": 5.2,
    "camera.pixel_size.units": Units.um,
    "camera.horizontal_number_of_pixels": 512,
    "camera.vertical_number_of_pixels": 512,
    "light_source.wavelength": 0.64,
    "light_source.wavelength.units": Units.um,
    "grating.period": 1000/300,
    "grating.period.units": Units.um,
    "lens_1.focal_length": 75,
    "lens_1.focal_length.units": Units.mm,
    "lens_1.clear_aperture": 45.72,
    "lens_1.clear_aperture.units": Units.mm,
    "lens_2.focal_length": 300,
    "lens_2.focal_length.units": Units.mm,
    "lens_2.clear_aperture": 45.72,
    "lens_2.clear_aperture.units": Units.mm,
    "pinhole.diameter": 30,
    "pinhole.diameter.units": Units.um,
    "misc.central_lobe_size_factor": 4,
}


def parse_inputs(data: dict[str, Any]) -> Inputs:
    """Converts the units of the input data from strings to Units instances."""
    data = data.copy()
    for key, value in data.items():
        if key.endswith(".units"):
            data[key] = Units[value]
    return data


def resolution(inputs: Inputs) -> Result:
    """Computes the radius of the Airy disk in the object space."""

    units = Units.um
    wav = inputs["light_source.wavelength"] * inputs["light_source.wavelength.units"].value
    value = 1.22 * wav / inputs["objective.numerical_aperture"] / units.value

    return {
        "value": value,
        "units": units,
        "name": "Resolution",
        "equation": r"\( \Delta \rho = \frac{ 1.22 \lambda }{ \text{NA}_{obj} }\)"
    }


def minimum_resolution(inputs: Inputs) -> Result:
    """Computes the minimum radius of the Airy disk in the object space for a given grating and objective magnification."""

    units = Units.um
    gr_period = inputs["grating.period"] * inputs["grating.period.units"].value
    value = gr_period / Units.um.value / 0.28 / inputs["objective.magnification"]

    return {
       "value": value,
       "units": units,
       "name": "Minimum resolution",
       "equation": r"\( \Delta \rho \ge \frac{\Lambda}{0.28 M_{obj}}  \)",
    }


def maximum_grating_period(inputs: Inputs) -> Result:
    """Computes the maximum period of the grating to ensure correct PSF sampling."""

    units = Units.um
    wav = inputs["light_source.wavelength"] * inputs["light_source.wavelength.units"].value
    value = wav * inputs["objective.magnification"] / 3 / inputs["objective.numerical_aperture"] / units.value

    return {
        "value": value,
        "units": units,
        "name": "Maximum grating period",
        "equation": r"\(\Lambda \le \frac{ \lambda M_{obj} }{3 \text{NA}_{obj}}\)"
    }


def maximum_pixel_size(inputs: Inputs) -> Result:
    """Computes the maximum pixel size that satisfies the sampling requirements given a grating period."""

    units = Units.um
    gr_period = inputs["grating.period"] * inputs["grating.period.units"].value
    mag_4f = actual_4f_magnification(inputs)["value"]
    value = gr_period * abs(mag_4f) / 2.67 / units.value

    return {
        "value": value,
        "units": units,
        "name": "Maximum pixel size",
        "equation": r"\( a \le \frac{ \Lambda |M_{4f}| }{ 2.67 }\)",
    }


def fourier_plane_spacing(inputs: Inputs) -> Result:
    """The position of the first diffraction order in the Fourier plane with respect to the optics axis.

    This assumes that the tangent of the diffracted angle is approximately equal to the angle itself.

    """

    units = Units.mm
    f1 = inputs["lens_1.focal_length"] * inputs["lens_1.focal_length.units"].value
    wav = inputs["light_source.wavelength"] * inputs["light_source.wavelength.units"].value
    gr_period = inputs["grating.period"] * inputs["grating.period.units"].value
    value = f1 * wav / gr_period / units.value

    return {
        "value": value,
        "units": units,
        "name": "Fourier plane spacing",
        "equation": r"\( \Delta x = \frac{ f_1 \lambda }{ \Lambda } \)"
    }


def fourier_plane_sizes(inputs: Inputs) -> Result:
    """Computes the radial extent of the image spectra in the Fourier plane.
    
    This ignores the broadening effects of aberrations such as coma, which can be obvious in the
    non-zero orders. It also assumes that the Abbe sine condition is satisfied.

    """
    units = Units.mm
    na_img_space = inputs["objective.numerical_aperture"] / inputs["objective.magnification"]  # image space NA of objective
    f1 = inputs["lens_1.focal_length"] * inputs["lens_1.focal_length.units"].value
    radius = na_img_space * f1 / units.value

    return {
        "value": radius,
        "units": units,
        "name": "Radial extent of image spectra",
        "equation": r"\( r = \text{NA}_{obj}' f_1 \)",
    }


def minimum_4f_magnification(inputs: Inputs) -> Result:
    """Computes the minimum magnification of the 4f system for sufficient PSF/fringe sampling."""

    units = None
    px_size = inputs["camera.pixel_size"] * inputs["camera.pixel_size.units"].value
    gr_period = inputs["grating.period"] * inputs["grating.period.units"].value
    wav = inputs["light_source.wavelength"] * inputs["light_source.wavelength.units"].value

    value = 2 * px_size* (1 / gr_period + inputs["objective.numerical_aperture"] / wav / inputs["objective.magnification"])

    return {
        "value": value,
        "units": units,
        "name": "Minimum 4f magnification (abs. value)",
        "equation": r"\( |M_{4f}| \ge 2a \left( \frac{1}{\Lambda} + \frac{ \text{NA}_{obj} }{ \lambda M_{obj} } \right) \)"
    }


def actual_4f_magnification(inputs: Inputs) -> Result:
    """Computes the actual magnification of the 4f system."""

    units = None
    f1 = inputs["lens_1.focal_length"] * inputs["lens_1.focal_length.units"].value
    f2 = inputs["lens_2.focal_length"] * inputs["lens_2.focal_length.units"].value
    value = -f2 / f1

    return {
        "value": value,
        "units": units,
        "name": "Actual 4f magnification",
        "equation": r"\( -f_2 / f_1 \)",
    }


def system_magnification(inputs: Inputs) -> Result:
    """Computes the magnification of the entire system."""

    units = None
    mag_4f = actual_4f_magnification(inputs)["value"]
    value = -inputs["objective.magnification"] * mag_4f

    return {
        "value": value,
        "units": units,
        "name": "System magnification",
        "equation": r"\( M_{obj} M_{4f} \)",
    }


def field_of_view_horizontal(inputs: Inputs) -> Result:
    """Computes the horizontal field of view in the object space."""

    units = Units.um
    px_size = inputs["camera.pixel_size"] * inputs["camera.pixel_size.units"].value
    mag_4f = actual_4f_magnification(inputs)["value"]

    value = inputs["camera.horizontal_number_of_pixels"] * px_size / inputs["objective.magnification"] / abs(mag_4f) / units.value

    return {
        "value": value,
        "units": units,
        "name": "Field of view (horizontal)",
        "equation": r"\( \text{FOV}_h = m \frac{ a } { M_{obj} |M_{4f}| } \)",
    }


def field_of_view_vertical(inputs: Inputs) -> Result:
    """Computes the vertical field of view in the object space."""

    units = Units.um
    px_size = inputs["camera.pixel_size"] * inputs["camera.pixel_size.units"].value
    mag_4f = actual_4f_magnification(inputs)["value"]

    value = inputs["camera.vertical_number_of_pixels"] * px_size / inputs["objective.magnification"] / abs(mag_4f) / units.value

    return {
        "value": value,
        "units": units,
        "name": "Field of view (vertical)",
        "equation": r"\( \text{FOV}_v = n \frac{ a } { M_{obj} |M_{4f}| } \)",
    }


def camera_diagonal(inputs: Inputs) -> Result:
    """Computes the length of the diagonal across the camera."""

    units = Units.mm
    px_size = inputs["camera.pixel_size"] * inputs["camera.pixel_size.units"].value
    num_px_h = inputs["camera.horizontal_number_of_pixels"]
    num_px_v = inputs["camera.vertical_number_of_pixels"]

    value = px_size * (num_px_h**2 + num_px_v**2)**(0.5) / units.value

    return {
        "value": value,
        "units": units,
        "name": "Camera diagonal",
        "equation": r"\( D = a \sqrt{m^2 + n^2} \)",
    }


def minimum_lens_1_na(inputs: Inputs) -> Result:
    """Computes the minimum NA of the first Fourier lens to avoid clipping the +1 diffracted order."""

    units = None
    wav = inputs["light_source.wavelength"] * inputs["light_source.wavelength.units"].value
    gr_period = inputs["grating.period"] * inputs["grating.period.units"].value

    value = wav / gr_period +  inputs["objective.numerical_aperture"] / inputs["objective.magnification"]

    return {
        "value": value,
        "units": units,
        "name": "Minimum NA of Fourier lens 1",
        "equation": r"\( \text{NA}_{L_1} \ge \frac{ \lambda }{ \Lambda } + \frac{\text{NA}_{obj}}{M_{obj}} \)",
    }


def minimum_lens_2_na(inputs: Inputs) -> Result:
    """Computes the minimum NA of the second Fourier lens to avoid clipping the +1 diffracted order."""

    units = None
    wav = inputs["light_source.wavelength"] * inputs["light_source.wavelength.units"].value
    gr_period = inputs["grating.period"] * inputs["grating.period.units"].value
    mag_4f = actual_4f_magnification(inputs)["value"]
    pinhole_diam = inputs["pinhole.diameter"] * inputs["pinhole.diameter.units"].value

    value =  wav / abs(mag_4f) / gr_period + 1.22 * wav / pinhole_diam

    return {
        "value": value,
        "units": units,
        "name": "Minimum NA of Fourier lens 2",
        "equation": r"\( \text{NA}_{L_2} \ge \frac{ \lambda }{ \Lambda |M_{4f}| } + 1.22 \frac{ \lambda} { d } \)",
    }


def lens_na(focal_length: float, clear_aperture: float) -> float:
    """Computes the NA of a lens assuming the Abbe sine condition is valid."""

    return clear_aperture / 2 / focal_length


def lens_1_na(inputs: Inputs) -> Result:
    """Computes the NA of the first Fourier lens."""

    units = None
    f1 = inputs["lens_1.focal_length"] * inputs["lens_1.focal_length.units"].value
    D = inputs["lens_1.clear_aperture"] * inputs["lens_1.clear_aperture.units"].value

    value = lens_na(f1, D)

    return {
        "value": value,
        "units": units,
        "name": "Actual NA of Fourier lens 1",
        "equation": r"\( \text{NA}_{L_1} = \frac{ D_1 }{ 2 f_1 } \)",
    }


def lens_2_na(inputs: Inputs) -> Result:
    """Computes the NA of the second Fourier lens."""

    units = None
    f2 = inputs["lens_2.focal_length"] * inputs["lens_2.focal_length.units"].value
    D = inputs["lens_2.clear_aperture"] * inputs["lens_2.clear_aperture.units"].value

    value = lens_na(f2, D)

    return {
        "value": value,
        "units": units,
        "name": "Actual NA of Fourier lens 2",
        "equation": r"\( \text{NA}_{L_2} = \frac{ D_2 }{ 2 f_2 } \)",
    }


def maximum_pinhole_diameter(inputs: Inputs) -> Result:
    """Compute the maximum pinhole diameter that ensures a uniform reference beam."""

    units = Units.um
    wav = inputs["light_source.wavelength"] * inputs["light_source.wavelength.units"].value
    f2 = inputs["lens_2.focal_length"] * inputs["lens_2.focal_length.units"].value
    cam_diag = camera_diagonal(inputs)
    cam_diag_norm = cam_diag["value"] * cam_diag["units"].value

    value = 2.44 * wav * f2 / cam_diag_norm / inputs["misc.central_lobe_size_factor"] / units.value

    return {
        "value": value,
        "units": units,
        "name": "Maximum pinhole diameter",
        "equation": r"\( d \le \frac{ 2.44 \lambda f_2 } { \gamma D} \)",
    }


def coupling_ratio(inputs: Inputs) -> Result:
    """Computes the ratio of the unscattered and scattered light beam radii in the Fourier plane.

    Notes
    -----

    > A ratio of 1 means that the diffraction spot is the same size as the FOV and only the DC
    > signal can be obtained. As the ratio approaches zero, more and more detail can be observed
    > within the image for a given FOV. [1]_

    .. [1] Bhaduri, et al., "Diffraction phase microscopy: principles and applications in materials
    and life sciences," Advances in Optics and Photonics 6, 57 (2014)

    """

    units = None

    res = resolution(inputs)
    fov_h = field_of_view_horizontal(inputs)
    fov_v = field_of_view_vertical(inputs)

    res_norm = res["value"] * res["units"].value
    fov_diag = ((fov_h["value"] * fov_h["units"].value)**2 + (fov_v["value"] * fov_v["units"].value)**2)**(0.5)

    value = res_norm / fov_diag

    return {
        "value": value,
        "units": units,
        "name": "Coupling ratio",
        "equation": r"\( \eta = \frac{ \Delta \rho }{ \text{FOV}_{\text{diagonal}}} \)",
    }


def compute_results(inputs: Inputs) -> dict[str, Result]:
    """Performs all design computations."""

    return {
        "resolution": resolution(inputs),
        "minimum_resolution": minimum_resolution(inputs),
        "camera_diagonal": camera_diagonal(inputs),
        "maximum_pixel_size": maximum_pixel_size(inputs),
        "field_of_view_horizontal": field_of_view_horizontal(inputs),
        "field_of_view_vertical": field_of_view_vertical(inputs),
        "maximum_grating_period": maximum_grating_period(inputs),
        "fourier_plane_spacing": fourier_plane_spacing(inputs),
        "fourier_plane_sizes": fourier_plane_sizes(inputs),
        "minimum_lens_1_na": minimum_lens_1_na(inputs),
        "minimum_lens_2_na": minimum_lens_2_na(inputs),
        "lens_1_na": lens_1_na(inputs),
        "lens_2_na": lens_2_na(inputs),
        "minimum_4f_magnification": minimum_4f_magnification(inputs),
        "4f_magnification": actual_4f_magnification(inputs),
        "system_magnification": system_magnification(inputs),
        "maximum_pinhole_diameter": maximum_pinhole_diameter(inputs),
        "coupling_ratio": coupling_ratio(inputs),
    }


def validate_4f_magnification(inputs: Inputs, results: dict[str, Result]) -> Optional[str]:
    """Validates that the magnification of the 4f system is greater than the minimum requirement."""

    mag_4f = abs(actual_4f_magnification(inputs)["value"])
    min_mag_4f = abs(minimum_4f_magnification(inputs)["value"])

    if mag_4f < min_mag_4f:
        return f"Absolute value of 4f magnification is less than the minimum requirement: Minimum: {min_mag_4f}, Actual: {mag_4f}"


def validate_lens_1_na(_, results: dict[str, Result]) -> Optional[str]:
    """Validates that the NA of lens 1 exceeds the minimum requirement."""
    
    lens_1_na = results["lens_1_na"]["value"]
    min_lens_1_na = results["minimum_lens_1_na"]["value"]

    if lens_1_na < min_lens_1_na:
        return f"NA of lens 1 is less than the minimum requirement: Minimum: {min_lens_1_na}, Actual: {lens_1_na}"


def validate_lens_2_na(_, results: dict[str, Result]) -> Optional[str]:
    """Validates that the NA of lens 2 exceeds the minimum requirement."""
    
    lens_2_na = results["lens_2_na"]["value"]
    min_lens_2_na = results["minimum_lens_2_na"]["value"]

    if lens_2_na < min_lens_2_na:
        return f"NA of lens 2 is less than the minimum requirement: Minimum: {min_lens_2_na}, Actual: {lens_2_na}"
    

def validate_pinhole_diameter(inputs: Inputs, results: dict[str, Result]) -> Optional[str]:
    """Validates that the pinhole diameter is less than the maximum requirement."""

    units = Units.um
    ph_diam = inputs["pinhole.diameter"] * inputs["pinhole.diameter.units"].value / units.value
    max_ph_diam = results["maximum_pinhole_diameter"]["value"] * results["maximum_pinhole_diameter"]["units"].value / units.value

    if ph_diam > max_ph_diam:
        return f"Pinhole diameter exceeds the maximum requirement: Maximum {max_ph_diam} {units}, Actual: {ph_diam} {units}"
    

def validate_pixel_size(inputs: Inputs, results: dict[str, Result]) -> Optional[str]:
    """Validates the pixel size is less than the maximum requirement."""

    units = Units.um
    px = inputs["camera.pixel_size"] * inputs["camera.pixel_size.units"].value / units.value
    max_px = results["maximum_pixel_size"]["value"] * results["maximum_pixel_size"]["units"].value / units.value

    if px > max_px:
        return f"Pixel size exceeds the maximum requirement: Maximum {max_px} {units}, Actual: {px} {units}"


def validate_grating_period(inputs: Inputs, results: dict[str, Result]) -> Optional[str]:
    """Validates the grating period is less than the maximum requirement."""

    units = Units.um
    gp = inputs["grating.period"] * inputs["grating.period.units"].value / units.value
    max_gp = results["maximum_grating_period"]["value"] * results["maximum_grating_period"]["units"].value / units.value

    if gp > max_gp:
        return f"Grating period exceeds the maximum requirement: Maximum {max_gp} {units}, Actual: {gp} {units}"


def validate_results(inputs: Inputs, results: dict[str, Result]) -> list[str]:
    """Validates whether the design criteria are satisfied."""

    validations = [
        validate_4f_magnification,
        validate_lens_1_na,
        validate_lens_2_na,
        validate_pinhole_diameter,
        validate_pixel_size,
        validate_grating_period,
    ]

    violations = []
    for validation in validations:
        violations.append(validation(inputs, results))

    return [v for v in violations if v is not None]


def plot_fourier_plane(inputs: Inputs, results: dict[str, Result]) -> str:
    """Create a plot of the areas of the Fourier plane after the first Fourier lens."""
    radius = results["fourier_plane_sizes"]["value"]
    units = results["fourier_plane_sizes"]["units"]

    spacing_tmp = fourier_plane_spacing(inputs)
    spacing = spacing_tmp["value"] * spacing_tmp["units"].value / units.value
    
    zero_order = plt.Circle((0, 0), radius, label="0")
    first_order = plt.Circle((spacing, 0), radius, label="+1")

    _, ax = plt.subplots() 
    ax.add_patch(zero_order)
    ax.add_patch(first_order)
    ax.set_xlim((-spacing - radius, spacing + radius))
    ax.set_ylim((-spacing - radius, spacing + radius))
    ax.spines[['right', 'top']].set_visible(False)
    ax.set_title("Diffracted Orders in the Fourier Plane")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.legend()

    # Encode image as base64 string for embedding in HTML
    byte_string = io.BytesIO()
    plt.savefig(byte_string, format='png')
    byte_string.seek(0)
    img_base64 = base64.b64encode(byte_string.read()).decode()

    return img_base64


def defaults_to_json(output_file: Path):
    """Writes the default inputs to a JSON file."""

    with output_file.open(mode="w", encoding="utf-8") as file:
        json.dump(DEFAULTS, file, indent=4, default=str)


def main(input_file: Path, output_file: Path):
    environment = Environment(loader=PackageLoader("kmdouglass.udesigner", "templates"))
    template = environment.get_template("dpm_design.html")

    with input_file.open(mode="r", encoding="utf-8") as file:
        unparsed_inputs = json.load(file)
        inputs = parse_inputs(unparsed_inputs)

    results = compute_results(inputs)
    violations = validate_results(inputs, results)
    plots = {"lens_1_fourier_plane": plot_fourier_plane(inputs, results)}

    content = template.render(inputs=inputs, results=results, violations=violations, plots=plots)

    with output_file.open(mode="w", encoding="utf-8") as file:
        file.write(content)
