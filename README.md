# ProtDomRetrieverSuite

ProtDomRetrieverSuite is an enhanced version of ProtDomRetriever, providing a comprehensive graphical interface and extended functionality for protein domain analysis. The suite maintains the core functionality of retrieving protein domain information from InterPro while adding support for AlphaFold structure downloads and domain-specific PDB structure processing.

Created by Nicolas-Frédéric Lipp, PhD.

## Features

### Core Features (from ProtDomRetriever)
- Retrieve domain information for multiple UniProtKB accessions
- Filter domains based on specified InterPro entries
- Select longest domains when multiple entries overlap
- Generate TSV output with domain ranges
- Create FASTA files for the retrieved protein domains

### New Features
- Modern-like graphical user interface with dark mode
- Real-time progress tracking and logging
- AlphaFold structure download integration
- PDB structure trimming based on domain ranges
- Improved error handling and recovery
- Multi-threaded processing for better performance

## Quick Installation

```bash
pip install git+https://github.com/yourusername/protdomretrieversuite.git
```

For detailed installation instructions, including system-specific setup and troubleshooting, see [INSTALL.md](INSTALL.md).

### Note for macOS Users (macOS Sequoia 15.0+)
If you're using macOS Sequoia, you might see messages in the terminal like:
```
"Python[XXXXX:XXXXX] +[IMKInputSession subclass]: chose IMKInputSession_Legacy"
```
This is a diagnostic message from macOS Sequoia's input method system. It is harmless, does not affect functionality, and can be safely ignored.

## Usage

### Starting the Application
```bash
protdomretrieversuite
```

### Using the Interface
1. Select an input file containing UniProtKB accessions (one per line)
2. Choose output directory for results (wherever you want on your computer)
3. Enter InterPro entries for domain filtering (as indicated, one per line or separated by comma)
4. Select optional processing steps:
   - FASTA sequence retrieval
   - AlphaFold structure download
   - PDB structure trimming

### Output Files
The suite generates several output files:
1. `domain_analysis.tsv`: Tab-separated file with comprehensive domain information
2. `domain_ranges.txt`: Text file listing domain ranges
3. `domain_sequences.fasta`: FASTA file of domain sequences (if selected)
4. `alphafold_structures/`: Directory containing downloaded AlphaFold structures
5. `trimmed_structures/`: Directory containing domain-trimmed PDB files

## Examples
Example datasets are provided in the `tests/seed_test` directory:
1. Test Dataset 1 (`input_test1.txt`, `entries_test1.txt`)
2. Test Dataset 2 (`input_test2.txt`, `entries_test2.txt`)
3. Test Dataset 3 (`input_test3.txt`, `entries_test3.txt`)

## Support
If you encounter any problems or have questions:
1. Check the log files in your output directory
2. Open an issue on the GitHub repository
3. Contact the developer through GitHub

## Author
Nicolas-Frédéric Lipp, PhD  
https://github.com/NicoFrL

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments
- InterPro database and API (with implemented rate limiting for responsible usage):
    https://interpro-documentation.readthedocs.io/en/latest/interpro.html
    https://interpro-documentation.readthedocs.io/en/latest/download.html
    https://github.com/ProteinsWebTeam/interpro7-api/tree/master/docs
    
- AlphaFold DB:
    https://alphafold.ebi.ac.uk/about
    https://alphafold.ebi.ac.uk/api-docs
- UniProt database:
    https://www.uniprot.org/help/about
    https://www.uniprot.org/help/programmatic_access
    

## Development Notes
This project was developed with the assistance of AI language models, which provided guidance on code structure, best practices, and documentation. The core algorithm and scientific approach were designed and implemented by the author.
