Supported File Formats
======================

SeaSenseLib supports reading data from various oceanographic instruments and file formats. This page provides a complete reference of all supported format keys.

Format Keys Reference
--------------------

Format keys can be used with ``ssl.read(filename, file_format='key')`` when automatic detection fails or you need to override the default reader choice.

ADCP (Acoustic Doppler Current Profiler)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- ``'adcp-matlab-uhhds'``: ADCP MATLAB UHHDS format
- ``'adcp-matlab-rdadcp'``: ADCP MATLAB RDADCP format

CSV/Generic Formats
~~~~~~~~~~~~~~~~~~~

- ``'csv'``: Comma-separated values format
- ``'netcdf'``: Network Common Data Form (CF-compliant)

Nortek Instruments
~~~~~~~~~~~~~~~~~~

- ``'nortek-ascii'``: Nortek ASCII format for Aquadopps (requires header file)

**Usage Example:**

.. code-block:: python

   # Nortek requires both data and header files
   data = ssl.read('aquadopp.dat', 
                   file_format='nortek-ascii',
                   header_file='aquadopp.hdr')

RBR (Richard Brancker Research)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- ``'rbr-rsk'``: RBR RSK native format (auto reader)
- ``'rbr-rsk-default'``: RBR RSK default reader
- ``'rbr-rsk-legacy'``: RBR RSK legacy format
- ``'rbr-matlab'``: RBR MATLAB export format
- ``'rbr-matlab-legacy'``: RBR MATLAB legacy format
- ``'rbr-matlab-rsktools'``: RBR MATLAB RSKtools export
- ``'rbr-ascii'``: RBR ASCII format

RCM (Anderaa)
~~~~~~~~~~~~~

- ``'rcm-matlab'``: RCM MATLAB format

SeaBird Electronics
~~~~~~~~~~~~~~~~~~~

- ``'sbe-cnv'``: SeaBird CNV format (CTD casts and time series)
- ``'sbe-ascii'``: SeaBird ASCII format

Seasun
~~~~~~

- ``'seasun-tob'``: Seasun TOB format

Usage Examples
--------------

**Automatic Detection (Recommended):**

.. code-block:: python

   import seasenselib as ssl
   
   # Let SeaSenseLib detect the format
   dataset = ssl.read('your_file.cnv')

**Explicit Format Specification:**

.. code-block:: python

   # When automatic detection fails
   dataset = ssl.read('data.txt', file_format='sbe-ascii')
   
   # For ambiguous extensions like .mat
   rbr_data = ssl.read('logger_export.mat', file_format='rbr-matlab')
   adcp_data = ssl.read('current_data.mat', file_format='adcp-matlab-uhhds')

**Multi-file Formats:**

.. code-block:: python

   # Nortek instruments require both data and header files
   nortek_data = ssl.read('current_meter.dat',
                          file_format='nortek-ascii',
                          header_file='current_meter.hdr')

When to Use Format Keys
-----------------------

Use explicit format specification when:

- Automatic detection fails
- Files have non-standard or ambiguous extensions (e.g., ``.txt``, ``.dat``, ``.mat``)
- You need to override the default reader choice
- Working with multi-file formats like Nortek instruments

Checking Available Formats
---------------------------

Use the command line to see all available readers:

.. code-block:: bash

   seasenselib list readers

This will show you the current list of supported formats in your SeaSenseLib installation.