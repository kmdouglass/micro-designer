"""Design for a multifocal Kohler integrator.

References
----------
.. [1] D. Mahecic, et. al, Nature Methods 17, 726-733 (2020).
   https://doi.org/10.1038/s41592-020-0859-z

"""

import json
from pathlib import Path
from typing import Optional, TypedDict

from jinja2 import Environment, PackageLoader
import numpy as np

from kmdouglass.udesigner import Result, Units, parse_inputs

Inputs = TypedDict(
    "Inputs",
    {
        "mla.focal_length": float,
        "mla.focal_length.units": Units,
        "mla.pitch": float,
        "mla.pitch.units": Units,
        "mla_ex.focal_length": float,
        "mla_ex.focal_length.units": Units,
        "mla_ex.pitch": float,
        "mla_ex.pitch.units": Units,
        "fourier_lens.focal_length": float,
        "fourier_lens.focal_length.units": Units,
        "collimating_lens.focal_length": float,
        "collimating_lens.focal_length.units": Units,
        "telescope.magnification": float,
        "source.radius": float,
        "source.radius.units": Units,
        "source.divergence": float,
        "source.divergence.units": Units,
        "source.wavelength": float,
        "source.wavelength.units": Units,
        "system.magnification": float,
    }
)


DEFAULTS: Inputs = {
    "mla.focal_length": 4.78, 
    "mla.focal_length.units": Units.mm,
    "mla.pitch": 300.0,
    "mla.pitch.units": Units.um,
    "mla_ex.focal_length": 6.0,  
    "mla_ex.focal_length.units": Units.mm, 
    "mla_ex.pitch": 222.0, 
    "mla_ex.pitch.units": Units.um, 
    "fourier_lens.focal_length": 300, 
    "fourier_lens.focal_length.units": Units.mm,  
    "collimating_lens.focal_length": 60.0, 
    "collimating_lens.focal_length.units": Units.mm,
    "telescope.magnification": 0.25,
    "source.radius": 1.0,
    "source.radius.units": Units.mm,
    "source.divergence": 100.0,
    "source.divergence.units": Units.mrad,
    "source.wavelength": 0.488,
    "source.wavelength.units": Units.um,
    "system.magnification": 116.0,
}


def flat_field_size(inputs: Inputs) -> Result:
    """Calculates the flat field size at the excitation microlens array."""
    units = Units.mm
    f_FL = inputs["fourier_lens.focal_length"] * inputs["fourier_lens.focal_length.units"].value
    p = inputs["mla.pitch"] * inputs["mla.pitch.units"].value
    f = inputs["mla.focal_length"] * inputs["mla.focal_length.units"].value
    value = f_FL * p / f / units.value

    return {
        "value": value,
        "units": units,
        "name": "Flat field size at excitation MLA",
        "equation": r"\( S = \frac{f_{FL} \times p}{f} \)",
    }


def flat_field_size_sample_plane(inputs: Inputs) -> Result:
    """Calculates the flat field size at the sample plane."""
    units = Units.um
    f_FL = inputs["fourier_lens.focal_length"] * inputs["fourier_lens.focal_length.units"].value
    p = inputs["mla.pitch"] * inputs["mla.pitch.units"].value
    f = inputs["mla.focal_length"] * inputs["mla.focal_length.units"].value
    mag = inputs["system.magnification"]

    value = f_FL * p / f / mag / units.value

    return {
        "value": value,
        "units": units,
        "name": "Flat field size at sample plane",
        "equation": r"\( S = \frac{1}{M_{sys}} \frac{f_{FL} \times p}{f} \)",
    }


def beam_radius_first_mla(inputs: Inputs) -> Result:
    units = Units.mm

    R_source = inputs["source.radius"] * inputs["source.radius.units"].value
    f_cl = inputs["collimating_lens.focal_length"] * inputs["collimating_lens.focal_length.units"].value
    theta_source = inputs["source.divergence"] * inputs["source.divergence.units"].value

    value = (R_source + f_cl * np.tan(theta_source)) / units.value

    return {
        "value": value,
        "units": units,
        "name": "Beam radius at first integrator MLA",
        "equation": r"\( R_{beam} = R_{source} + f_{CL} * \tan \left( \theta_{source} \right) \)"
    }


def excitation_spot_size(inputs: Inputs) -> Result:
    units = Units.um
    R_beam = beam_radius_first_mla(inputs)
    R_beam = R_beam["value"] * R_beam["units"].value

    f = inputs["mla.focal_length"] * inputs["mla.focal_length.units"].value
    f_ex = inputs["mla_ex.focal_length"] * inputs["mla_ex.focal_length.units"].value
    f_fl = inputs["fourier_lens.focal_length"] * inputs["fourier_lens.focal_length.units"].value
    f_cl = inputs["collimating_lens.focal_length"] * inputs["collimating_lens.focal_length.units"].value
    R_source = inputs["source.radius"] * inputs["source.radius.units"].value
    mag_telescope = inputs["telescope.magnification"]

    value = (f * f_ex / mag_telescope / f_fl / f_cl * R_source + f_ex * mag_telescope / f_fl * R_beam) / units.value

    return {
        "value": value,
        "units": units,
        "name": "Spot size in focal plane of excitation MLA",
        "equation": r"\( r = \frac{f \times f_{ex}}{f_{FL} f_{CL} M_{tel}} R_{source} + \frac{f_{ex} M_{tel}}{f_{FL}} R_{beam} \)",
    }


def excitation_spot_size_sample_plane(inputs: Inputs) -> Result:
    units = Units.um
    r_sample = excitation_spot_size(inputs)
    r_sample = r_sample["value"] * r_sample["units"].value

    mag_system = inputs["system.magnification"]

    value = r_sample / mag_system / units.value

    return {
        "value": value,
        "units": units,
        "name": "Spot size in sample plane",
        "equation": r"\( r_{sample} = \frac{1}{M_{sys}} \left( \frac{f \times f_{ex}}{f_{FL} f_{CL} M_{tel}} R_{source} + \frac{f_{ex} M_{tel}}{f_{FL}} R_{beam} \right) \)",
    }


def homogeneity(inputs: Inputs) -> Result:
    R_beam = beam_radius_first_mla(inputs)
    R_beam = R_beam["value"] * R_beam["units"].value
    pitch = inputs["mla.pitch"] * inputs["mla.pitch.units"].value

    value = R_beam / pitch

    return {
        "value": value,
        "units": None,
        "name": "Homogeneity",
        "equation": r"\( B = \frac{R_{beam}}{p} \)",
    }


def fresnel_number(inputs: Inputs) -> Result:
    units = None
    p = inputs["mla.pitch"] * inputs["mla.pitch.units"].value
    f = inputs["mla.focal_length"] * inputs["mla.focal_length.units"].value
    wavelength = inputs["source.wavelength"] * inputs["source.wavelength.units"].value

    value = p * p / 4 / f / wavelength

    return {
        "value": value,
        "units": units,
        "name": "Fresnel number",
        "equation": r"\( F = \frac{p^2}{4 f \lambda} \)",
    }


def compute_results(inputs: Inputs) -> dict[str, Result]:
    """Performs all design computations."""

    return {
        "flat_field_size": flat_field_size(inputs),
        "flat_field_size_sample_plane": flat_field_size_sample_plane(inputs),
        "excitation_spot_size": excitation_spot_size(inputs),
        "excitation_spot_size_sample_plane": excitation_spot_size_sample_plane(inputs),
        "beam_radius_mla": beam_radius_first_mla(inputs),
        "homogeneity": homogeneity(inputs),
        "fresnel_number": fresnel_number(inputs),
    }


def validate_fresnel_number(inputs: Inputs, results: dict[str, Result]) -> Optional[str]:
    """Validates whether the Fresnel number is greater than or equal to 5."""

    fresnel_number = results["fresnel_number"]["value"]
    target = 5
    if fresnel_number < target:
        return f"Fresnel number ({fresnel_number}) should be greater than or equal to {target} for good homogeneity."


def validate_homogeneity(inputs: Inputs, results: dict[str, Result]) -> Optional[str]:
    """Validates whether the homogeneity is greater than or equal to 5."""

    homogeneity = results["homogeneity"]["value"]
    target = 5
    if homogeneity < target:
        return f"Homogeneity ({homogeneity}) should be less than or equal to {target} for good homogeneity."

def validate_crosstalk(inputs: Inputs, results: dict[str, Result]) -> Optional[str]:
    """Validates that there is no crosstalk between lenslets."""
    mag_tel = inputs["telescope.magnification"]
    f = inputs["mla.focal_length"] * inputs["mla.focal_length.units"].value
    f_cl = inputs["collimating_lens.focal_length"] * inputs["collimating_lens.focal_length.units"].value
    R_source = inputs["source.radius"] * inputs["source.radius.units"].value
    p = inputs["mla.pitch"] * inputs["mla.pitch.units"].value

    value = f / mag_tel / f_cl * R_source
    target = p / 2

    if value > target:
        return f"Crosstalk ({value}) should be less than or equal to {target} for good homogeneity."


def validate_results(inputs: Inputs, results: dict[str, Result]) -> list[str]:
    """Validates whether the design criteria are satisfied."""

    validations = [
        validate_fresnel_number,
        validate_homogeneity,
        validate_crosstalk,
    ]

    violations = []
    for validation in validations:
        violations.append(validation(inputs, results))

    return [v for v in violations if v is not None]


def defaults_to_json(output_file: Path):
    """Writes the default inputs to a JSON file."""

    with output_file.open(mode="w", encoding="utf-8") as file:
        json.dump(DEFAULTS, file, indent=4, default=str)


def main(input_file: Path, output_file: Path) -> None:
    environment = Environment(loader=PackageLoader("kmdouglass.udesigner", "templates"))
    template = environment.get_template("mfki_design.html")

    with input_file.open(mode="r", encoding="utf-8") as file:
        unparsed_inputs = json.load(file)
        inputs = parse_inputs(unparsed_inputs)

    results = compute_results(inputs)
    violations = validate_results(inputs, results)
    plots = {}

    content = template.render(inputs=inputs, results=results, violations=violations, plots=plots)

    with output_file.open(mode="w", encoding="utf-8") as file:
        file.write(content)
