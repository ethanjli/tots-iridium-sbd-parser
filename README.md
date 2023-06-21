# tots-iridium-sbd-parser

Parser for Iridium SBD MO messages from Iridium Solar Edge devices, for sediment traps in the Tale of Three Systems project on R/V Sikuliaq in June-July 2023.

This provides a small and simple command-line tool to decode an SBD file and display some basic information encoded in the file.

## Usage

To use this tool, it's recommended to [install pipx](https://pypa.github.io/pipx/) and then use pipx to install this tool, via:
```
pipx install git+https://github.com/ethanjli/tots-iridium-sbd-parser.git
```

### Development

If you already have [Poetry installed](https://python-poetry.org/docs/), you can run `poetry install` and then `poetry run cli [filename]`, where `[filename]` should be replaced with the file path of the Iridium SBD MO (mobile-originated) file you're trying to parse.


## Licensing

We have chosen the following licenses in order to give away our work for free, so that you can freely use for whatever purposes you have, with minimal restrictions while still protecting our disclaimer that this work is provided without any warranties at all. If you're using this project, or if you have questions about the licenses, we'd love to hear from you - please start a new discussion thread in the "Discussions" tab of this repository on Github or email us at lietk12@gmail.com .

Note: this project started as a fork of the BSD-licensed project https://github.com/castelao/iridiumSBD (which is now archived and unmaintained), but ended up replacing all existing code. So it's effectively a new project at this point.

### Software

Except where otherwise indicated in this repository, software files provided here are covered by the following information:

**Copyright Prakash Lab and template-permissive project contributors**

SPDX-License-Identifier: `Apache-2.0 OR BlueOak-1.0.0`

Software files in this project are released under the [Apache License v2.0](https://www.apache.org/licenses/LICENSE-2.0) and the [Blue Oak Model License 1.0.0](https://blueoakcouncil.org/license/1.0.0); you can use the source code provided here under the Apache License or under the Blue Oak Model License, and you get to decide which license you will agree to. We are making the software available under the Apache license because it's [OSI-approved](https://writing.kemitchell.com/2019/05/05/Rely-on-OSI.html) and it goes well together with the [Solderpad Hardware License](https://solderpad.org/licenses/SHL-2.1/), which is an open hardware license used in various projects released by the Prakash Lab; but we like the Blue Oak Model License more because it's easier to read and understand. Please read and understand the licenses for the specific language governing permissions and limitations.

### Everything else

Except where otherwise indicated in this repository, any other files (such as images, media, data, and textual documentation) provided here not already covered by software or hardware licenses (described above) are instead covered by the following information:

**Copyright Prakash Lab and template-permissive project contributors**

SPDX-License-Identifier: `CC-BY-4.0`

Files in this project are released under the [Creative Commons Attribution 4.0 International License](http://creativecommons.org/licenses/by/4.0/). Please read and understand the license for the specific language governing permissions and limitations.
