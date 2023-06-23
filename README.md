# tots-iridium-sbd-parser

Parser for Iridium SBD MO messages from Iridium Solar Edge devices, for sediment traps in the Tale of Three Systems project on R/V Sikuliaq in June-July 2023.

This provides a set of simple command-line tools to decode SBD messages and the information encoded in the messages.

## Usage

To use these tools, it's recommended to [install pipx](https://pypa.github.io/pipx/) and then use pipx to install the tools, via the following command in your terminal:
```
pipx install git+https://github.com/ethanjli/tots-iridium-sbd-parser.git
```

Then you can run the `tots-sbd-decode` tool (for decoding a single SBD file) in your terminal as:
```
tots-sbd-decode [sbd-filename]
```
where you should replace `[sbd-filename]` with the path of the Iridium SBD MO (mobile-originated) file you're trying to parse. If you want to decode an SBD MO message with a 3DES-encrypted payload, you can also provide a key file:
```
tots-sbd-decode [sbd-filename] --key [key-filename]
```
where you should replace `[key-filename]` with the path of the key file you want to use. The key file should consist of a 48-character hex-encoded string, for example:
```
8DE483E58FE9DFE3FCB3EE48C29C77850DEB7BBDC4EE6808
```

If you'd instead prefer to decode all SBD files in a CSV history report file downloaded from MetOcean LiNC, you can run the `tots-report-decode` tool in your terminal as:
```
tots-report-decode [report-filename]
```
where you should replace `[report-filename]` with the path of the history report CSV file you're trying to parse. You can also provide a set of decryption keys, so that keys will automatically be selected as needed based on the IMEI associated with each SBD message included in the report CSV file:
```
tots-sbd-decode [report-filename] --keys [keys-directory-path]
```
where you should replace `[keys-directory-path]` with the path of a directory which has keyfiles (of the same format as the keys used by `tots-sbd-decode`) whose filenames are of format `[IMEI].3des-key` (e.g. `300434064056620.3des-key`) where the IMEI in the key's filename matches the IMEI specified in some row of the history report CSV file.

### Development

If you already have [Poetry installed](https://python-poetry.org/docs/), you can run `poetry install` and then you can run any of the commands listed above, replacing `tots-sbd-decode` with `poetry run tots-sbd-decode` and `tots-report-decode` with `poetry run tots-report-decode`.


## Licensing

We have chosen the following licenses in order to give away our work for free, so that you can freely use it for whatever purposes you have, with minimal restrictions while still protecting our disclaimer that this work is provided without any warranties at all. If you're using this project, or if you have questions about the licenses, we'd love to hear from you - please start a new discussion thread in the "Discussions" tab of this repository on Github or email us at lietk12@gmail.com .

Note: this project started as a fork of the BSD-licensed project https://github.com/castelao/iridiumSBD (which is now archived and unmaintained), but ended up replacing all existing code. So it's effectively a new project at this point.

### Software

Except where otherwise indicated in this repository, software files provided here are covered by the following information:

**Copyright Ethan Li**

SPDX-License-Identifier: `Apache-2.0 OR BlueOak-1.0.0`

Software files in this project are released under the [Apache License v2.0](https://www.apache.org/licenses/LICENSE-2.0) and the [Blue Oak Model License 1.0.0](https://blueoakcouncil.org/license/1.0.0); you can use the source code provided here under the Apache License or under the Blue Oak Model License, and you get to decide which license you will agree to. I am making the software available under the Apache license because it's [OSI-approved](https://writing.kemitchell.com/2019/05/05/Rely-on-OSI.html) and it goes well together with the [Solderpad Hardware License](https://solderpad.org/licenses/SHL-2.1/), which is an open hardware license used in various projects I have worked on; but I like the Blue Oak Model License more because it's easier to read and understand. Please read and understand the licenses for the specific language governing permissions and limitations.

### Everything else

Except where otherwise indicated in this repository, any other files (such as images, media, data, and textual documentation) provided here not already covered by software or hardware licenses (described above) are instead covered by the following information:

**Copyright Ethan Li**

SPDX-License-Identifier: `CC-BY-4.0`

Files in this project are released under the [Creative Commons Attribution 4.0 International License](http://creativecommons.org/licenses/by/4.0/). Please read and understand the license for the specific language governing permissions and limitations.
