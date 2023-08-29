# Micro-Designer

Design tools for microscopes

## Getting Started

### Installation

```console
pip install kmdouglass-udesigner
```

### Usage

 Run the following commands to 
 
 1. first generate a JSON template for the microscope design parameters, and then
 2. create a HTML design document for a diffraction phase microscope.

```console
# Create an inputs template that you can edit
udesign -t dpm inputs -o inputs.json

# Create an HTML design document for the microscope
udesign -t dpm doc -i inputs.json -o output.html
```

## Supported Types of Microscopes

- [Diffraction Phase](https://doi.org/10.1364/OL.31.000775)
- [Multifocal Koehler Integrator](https://doi.org/10.1038/s41592-020-0859-z)

To see the names of the corresponding types, run the following command:

```console
udesign -h
```
