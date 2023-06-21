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
