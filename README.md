# SeaSenseLib

A tool for reading, converting, and plotting sensor data from different oceanographic formats. 

## Table of Contents

- [Installation](#installation)
- [How to Use SeaSenseLib](#how-to-use-seasenselib)
- [CLI Usage](#cli-usage)
- [Example data](#example-data)
  - [Converting a CNV file to netCDF](#converting-a-cnv-file-to-netcdf)
  - [Showing the summary of a netCDF](#showing-the-summary-of-a-netcdf)
  - [Plotting a T-S diagram, depth profile and time series](#plotting-a-t-s-diagram-depth-profile-and-time-series)
- [Extending SeaSenseLib with Plugins](#extending-seasenselib-with-plugins)
- [Development](#development)

## Installation

To install SeaSenseLib, we strongly recommend using a scientific Python distribution. 
If you already have Python, you can install SeaSenseLib with:

```bash
pip install seasenselib
```

Now you're ready to use the library.

## How to Use SeaSenseLib

SeaSenseLib is designed to make working with oceanographic data easy and intuitive, whether you're analyzing CTD profiles, processing mooring data, or creating publication-ready plots in Jupyter notebooks.

### Quick Start - Basic Workflow

The most common workflow: read sensor data, analyze it, create plots, and save results.

```python
import seasenselib as ssl

# 1. Read CTD data (auto-detects .cnv format)
ds = ssl.read("profile.cnv")

# 2. Quick data overview
print(ds)

# 3. Create plots
ssl.plot('time-series', ds, parameters=['temperature', 'salinity'])
ssl.plot('ts-diagram', ds) 

# 4. Save data as netCDF (auto-detects .nc format)
ssl.write(ds, 'profile.nc')
```

### Working with Different Data Formats

SeaSenseLib supports different oceanographic instruments. Here's how to work with different formats by specifying the format or letting it auto-detect based on file extension:

```python
import seasenselib as ssl

# Seabird CTD data
sbe_data = ssl.read("station_001.cnv", file_format='sbe-cnv')

# RBR logger data  
rbr_data = ssl.read("temperature_logger.rsk", file_format='rbr-rsk')

# See all supported readers
readers = ssl.list_readers()
for reader in readers:
    print(f"- {reader['key']:<20} : {reader['name']} ")

# Auto-detect format from file extension
data = ssl.read("myfile.cnv")  # Automatically detects 'sbe-cnv'
```

### Using Reader, Writer, and Plotter Classes Directly

Example code for using SeaSenseLib with explicit usage of reader, writer, and plotter classes:

```python
import seasenselib as ssl

# Read CTD data from CNV file
reader = ssl.readers.SbeCnvReader("profile.cnv")
ds = reader.data

# Write dataset with CTD data to netCDF file
writer = ssl.writers.NetCdfWriter(ds)
writer.write('profile.nc')

# Plot CTD data
plotter = ssl.plotters.TimeSeriesPlotter(ds)
plotter.plot(parameters=['temperature'])
```

## CLI Usage

You can use the library for reading, converting, and plotting data based on different sensor files.
This chapter describes how to run the program from CLI. 

After installing as a Python package, you can run it via CLI by just using the package name: 

```bash
seasenselib
```
The various features of the library can be executed by using different commands. To invoke a command, simply append 
it as an argument to the program call via CLI (see following example section for some examples). The 
following table gives a short overview of the available commands.

| Command | Description |
|---|---|
| `list` | Display all supported input file formats, output file formats, and plot types. |
| `convert` | Converts a file of a specific instrument format to a netCDF, CSV, or Excel file. |
| `show` | Shows the summary for a input file of a specific instrument format.  |
| `plot` | Plots data from the input file using a specified plot type. |

Every command uses different parameters. To get more information about how to use the 
program and each command, just run it with the `--help` (or `-h`) argument:

```bash
seasenselib --help
```

To get help for a single command, add `--help` (or `-h`) argument after typing the command name:

```bash
seasenselib convert --help
```

## Example data

In the `examples` directory of the [code repository](https://github.com/ocean-uhh/seasenselib) you'll find example files from real research cruises.

- The file `sea-practical-2023.cnv` contains data from a vertical CTD profile (one downcast) with parameters `temperature`, `salinity`, `pressure`, `oxygen`, `turbidity`.
- The file `denmark-strait-ds-m1-17.cnv` contains data from an instrument moored over six days in a depth of around 650 m with parameters `temperature`, `salinity`, `pressure`.

The following examples will guide you through all available commands using the file `sea-practical-2023.cnv`. (Please note: these examples are the simplest way to work with data. The behavior of the program can be adjusted with additional arguments, as you can figure out by calling the help via CLI.)

### Converting a CNV file to netCDF

Use the following command to convert a CNV file to a netCDF file:

```bash
seasenselib convert -i examples/sea-practical-2023.cnv -o output/sea-practical-2023.nc
```

As you can see, format detection works for this command via file extension (`.nc` for netCDF or `.csv` for CSV), but you can also specify it via argument `--format` (or `-f`).

### Parameter Mapping

Important note: Our example files work out of the box. But in some cases your Seabird CNV files are using column names (so called "channels") for the parameter values, which
are not known of our program or the `pycnv` library which we're using. If you get an error due to missing parameters while converting or if you miss parameters during further data processing, e.g. something essential like the temperature, then a parameter mapping might be necessary. A parameter mapping is performed with the argument `--mapping` (or `-m`), which is followed by a list of mapping pairs separated with spaces. A mapping pair consists of a standard parameter name that we use within the program and the corresponding name of the column or channel from the Seabird CNV file. Example for a mapping which works for the example above:

```bash
seasenselib convert -i examples/sea-practical-2023.cnv -o output/sea-practical-2023.nc -m temperature=tv290C pressure=prdM salinity=sal00 depth=depSM
```

### Showing the summary of a netCDF

For the created netCDF file:

```bash
seasenselib show -i output/sea-practical-2023.nc
```

Format detection works also for this command via file extension (`.nc` for netCDF).

### Plotting a T-S diagram, depth profile and time series from a netCDF file

Plot a T-S diagram:

```bash
seasenselib plot ts-diagram -i examples/sea-practical-2023.cnv
```

Plot a CTD depth profile:

```bash
seasenselib plot depth-profile -i examples/sea-practical-2023.cnv
```

Plot a time series for 'temperature' parameter:

```bash
seasenselib plot time-series -i examples/sea-practical-2023.cnv -p temperature salinity --dual-axis
```

To save the plots into a file instead showing on screen, just add the parameter `--output` (or `-o`) followed by the path of the output file. 
The file extension determines in which format the plot is saved. Use `.png` for PNG, `.pdf` for PDF, and `.svg` for SVG.

## Extending SeaSenseLib with Plugins

SeaSenseLib supports a plugin system that allows you to add support for additional data formats without modifying the core library. Plugins use Python entry points for automatic discovery.

### Quick Start

**1. Install the example plugin:**

```bash
pip install examples/example-plugin
```

**2. Use it immediately:**

```bash
# Plugin appears automatically (here: example-json)
seasenselib list readers

# Use like any built-in format
seasenselib convert -i examples/example-plugin/data.json -o output.nc
```

### Creating Your Own Plugin

**1. Create a reader class:**

```python
# my_plugin/my_reader.py
from seasenselib.readers.base import AbstractReader
import xarray as xr

class MyFormatReader(AbstractReader):
    def __init__(self, input_file: str):
        self.input_file = input_file
        self._read_file()

    def _read_file(self):
        # Implement your file reading logic here.
        # For example, read the file and store data in self.data
        pass
    
    @staticmethod
    def format_key() -> str:
        return "my-format"
    
    @staticmethod
    def format_name() -> str:
        return "My Custom Format"
    
    @staticmethod
    def file_extension() -> str:
        return ".myf"
```

**2. Register via entry points in `pyproject.toml`:**

```toml
[project.entry-points."seasenselib.readers"]
my_format = "my_plugin.my_reader:MyFormatReader"
```

**3. Install and use:**

```bash
pip install -e .
seasenselib convert -i data.myf -o output.nc 
```

### Plugin Requirements

Your plugin must:
- Inherit from `AbstractReader`, `AbstractWriter`, or `AbstractPlotter`
- Implement `format_key()` and `format_name()` class methods (using `@classmethod`)
- Provide a `data` property (for readers) or `write()` method (for writers)

### Resources

- **[Example Plugin](examples/example-plugin/)** - Working reference implementation (JSON reader/writer)
- **Entry Point Groups**: `seasenselib.readers`, `seasenselib.writers`, `seasenselib.plotters`

## Development

Start here to set up your local development environment: clone the repository, create and activate a Python virtual environment, install all dependencies, and run tests or build the package. These steps ensure you work in an isolated, reproducible setup so you can experiment with the code, add new features, or fix issues before submitting changes.

1. **Clone the repo**  

   ```bash
   git clone https://github.com/ocean-uhh/seasenselib.git
   cd seasenselib
   ```

2. **Create and activate a virtual environment**

   - Linux/macOS:

     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

   - Windows (CMD):

     ```
     python -m venv venv
     venv\Scripts\activate.bat
     ```

   - Windows (PowerShell):

     ```
     python -m venv venv
     venv\Scripts\Activate.ps1
     ```

3. **Upgrade packaging tools and install dependencies**

   ```bash
   pip install --upgrade pip setuptools wheel
   pip install -e ".[dev]"
   ```

The environment is now ready.

Useful commands: 

- **Run tests**

  ```bash
  python -m unittest discover tests/
  ```

- **Execute the application**

  ```bash
  python -m seasenselib
  ```

- **Build distributions**

  ```bash
  python -m build
  ```

- **Deactivate/Quit the virtual environment**

  ```bash
  deactivate
  ```

