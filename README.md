# Code and data for "Disentangling individual and interactive hydrological effects of human activities in the Mu Us Sandy Land: An integrated modelling approach"

## Overview

This repository contains selected model inputs, processing scripts, simulation outputs, and figures associated with the study **“Disentangling individual and interactive hydrological effects of human activities in the Mu Us Sandy Land: An integrated modelling approach”**. The study investigates groundwater and related ecohydrological responses to vegetation restoration, agricultural irrigation, and coal mining in the Mu Us Sandy Land, northern China.

The workflow combines a regional ParFlow-CLM model at approximately 1 km resolution with eight factorial scenarios to examine individual effects and nonlinear interactions among these activities. The target hydrological year is October 2018–September 2019.

The archive contains selected processed products rather than a complete model rerun package. Meteorological forcing files, complete scenario execution configurations, raw simulation time series, and all manuscript analysis scripts are not identified in the supplied inventory. See the reproducibility and verification notes below.

## Study area and model grid

The study domain extends from 107.3–110.6° E and 37.4–39.4° N. It contains 330 × 200 horizontal grid cells and 10 vertical layers. The geographic domain is described at 0.01° , corresponding approximately to the nominal 1 km model resolution. Exact ParFlow grid spacing, georeferencing, and array orientation must be taken from the model configuration and processing scripts; a NumPy array alone does not store these geographic definitions.

## Repository structure

The supplied archive is named `20261025\_code`. Directory and file names below follow the current inventory.

```text
20261025\_code/
├── 1\\\_input\\\_data/
│   ├── clm\\\_input/
│   │   ├── drv\\\_clmin\\\_2004.dat
│   │   ├── drv\\\_clmin\\\_2019.dat
│   │   ├── drv\\\_vegm.alluv2000.dat
│   │   ├── drv\\\_vegm.alluv2019.dat
│   │   └── drv\\\_vegp.dat
│   ├── forcings/
│   │   └── Readme.txt
│   └── pfb\\\_files/
│       ├── DTB.pfb / DTB.sa
│       ├── IndicatorFile.pfb / IndicatorFile.sa
│       ├── mannings2000\\\_new.pfb
│       ├── mannings2019\\\_new.pfb
│       ├── mao.out.porosity.pfb
│       ├── permeability.pfb / permeability.sa
│       ├── slopex.pfb / slopey.pfb
│       └── sa2pfb.sh / sa2pfb.tcl
├── 2\\\_codes\\\_and\\\_outputs/
│   ├── 1\\\_WTD\\\_daily                   # S1–S8 WTD arrays; run\\\_WTD.py
│   ├── 2\\\_q\\\_new                        # Six-station streamflow; S1–S8
│   ├── 3\\\_ET                           # Eight ET arrays; run\\\_ET.py
│   ├── 4\\\_1\\\_gradient\\\_darcy             # Gradient diagnostics; S1–S3
│   ├── 4\\\_2\\\_rootzone\\\_water\\\_availability # Root-zone diagnostics; S1–S3
│   ├── 4\\\_3\\\_veg\\\_trans\\\_mmday            # Transpiration diagnostics; S1–S3
│   ├── 4\\\_4\\\_sh                         # Sensible heat arrays; S1–S8
│   └── 4\\\_5\\\_lh                         # Latent heat arrays; S1–S8
├── 3\\\_fig
│   └── figure1.png ... figure16.png
└── inventory\\\_upload\\\_folder.py
```

Entries separated by `/` on the same line represent separate files. This README is supplied separately for placement in the archive root.

## Scenario interpretation

The three factors are vegetation restoration (A), agricultural irrigation (B), and coal mining (C). Factor states describe the prescribed human-activity settings; all scenarios use the same target simulation period.

|Scenario|Vegetation|Irrigation|Coal mining|
|-|-|-|-|
|S1|Post-restoration|Off|Off|
|S2|Pre-restoration|Off|Off|
|S3|Post-restoration|On|Off|
|S4|Post-restoration|Off|On|
|S5–S7|Remaining three factorial combinations; verify individual labels against the manuscript scenario table and run configurations|See scenario table|See scenario table|
|S8|Post-restoration|On|On|

Conditional activity-specific responses are defined as S1 − S2 for vegetation restoration, S3 − S1 for irrigation, and S4 − S1 for coal mining. The complete combined response relative to the pre-restoration reference is S8 − S2. Conditional contrasts and effects averaged across the full factorial ensemble are different quantities and should retain their respective definitions.

## Main file formats

|Format|Description|
|-|-|
|`.py`|Python processing or inventory scripts|
|`.tcl`|ParFlow/PFTools conversion or station-processing scripts|
|`.sh`|Linux/HPC shell scripts|
|`.pfb`|ParFlow binary spatial fields|
|`.sa`|ParFlow simple ASCII fields|
|`.dat`|CLM input and parameter files|
|`.npy`|NumPy arrays|
|`.csv`|Gridded fields, station series, or regional statistics|
|`.txt`|Text outputs, summaries, or documentation|
|`.png`|Station plots and manuscript figures|

## Software requirements

The original workflow documentation reports the following software versions. These have not been verified against the archived scripts or an environment lock file.

* ParFlow **v3.13.0** with its integrated CLM land-surface module
* Python **3.12.4**
* NumPy **1.26.4**
* pandas **2.2.2**
* Matplotlib **3.8.4**
* Tcl/Tk and ParFlow PFTools

Individual scripts may require additional packages. ParFlow and its Python interface must be configured for scripts that read PFB files. A complete dependency file is not listed in the inventory.

## Reproducibility notes

The scripts may contain paths that are specific to the original Windows workstation or Linux/HPC environment. Users should update these paths before running the workflow. Shell (.sh) and Tcl (.tcl) files should retain LF line endings for execution under Linux.

## Authors and contact

Jiaxin Lei, Beijing Normal University

Email: jiaxinlei@mail.bnu.edu.cn

## License

Code: MIT License

Author-generated outputs: CC BY 4.0

