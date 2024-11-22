# protdomretrieversuite/processors/pdb_trimmer.py
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import json
import re


from protdomretrieversuite.processors.base_processor import BaseProcessor, ProcessorConfig
from protdomretrieversuite.utils.errors import (
    handle_processing_errors,
    ProcessingError,
    ValidationError,
    FileError
)

@dataclass
class PDBTrimmerConfig(ProcessorConfig):
    """PDB trimmer specific configuration.
    
    Attributes:
        output_subdir: Directory name for trimmed structures
        domain_pattern: Regex pattern for parsing domain ranges
        accept_custom_pdbs: Whether to allow non-AlphaFold PDB files
        custom_pdb_strict: If True, requires exact accession match; if False, allows partial matches
    """
    output_subdir: str = "trimmed_structures"
    domain_pattern: re.Pattern = re.compile(r'(\w+)\[(\d+)-(\d+)\]')
    accept_custom_pdbs: bool = False
    custom_pdb_strict: bool = False

class PDBTrimmer(BaseProcessor):
    """Handles PDB structure trimming based on domain ranges.
    
    Supports both AlphaFold and custom PDB structures.
    """

    @handle_processing_errors
    def process(self, pdb_dir: Path, domain_ranges: Path) -> Dict[str, Path]:
        """Process and trim PDB structures.
        
        Args:
            pdb_dir: Directory containing PDB files
            domain_ranges: File containing domain ranges
            
        Returns:
            Dictionary mapping domain identifiers to trimmed structure paths
        """
        # Validate inputs
        if not pdb_dir.exists():
            raise ValidationError(f"PDB directory not found: {pdb_dir}")
        if not domain_ranges.exists():
            raise ValidationError(f"Domain ranges file not found: {domain_ranges}")

        try:
            self.logger.info("Starting PDB trimming process")
            ranges = self._parse_domain_ranges(domain_ranges)
            
            output_dir = Path(self.config.output_dir) / self.config.output_subdir
            output_dir.mkdir(parents=True, exist_ok=True)
            
            results = {}
            total_domains = sum(len(domains) for domains in ranges.values())
            processed = 0
            pdb_sources = {}  # Track source of each PDB (AlphaFold or custom)
            found_files = 0
            missing_files = 0

            for accession, domains in ranges.items():
                pdb_file = self._find_pdb_file(pdb_dir, accession)
                if not pdb_file:
                    missing_files += 1
                    self.logger.warning(f"No PDB file found for {accession}")
                    continue
                    
                found_files += 1
                # Log the PDB source
                is_alphafold = "AF-" in pdb_file.name
                pdb_sources[accession] = "AlphaFold" if is_alphafold else "Custom PDB"
                self.logger.info(f"Processing {pdb_sources[accession]} structure: {pdb_file.name}")

                for domain_num, (start, end) in enumerate(domains, 1):
                    try:
                        output_name = f"{accession}_domain{domain_num}_trimmed.pdb"
                        output_path = output_dir / output_name
                        
                        self._trim_pdb_file(pdb_file, output_path, start, end)
                        results[f"{accession}_domain{domain_num}"] = output_path
                        
                        processed += 1
                        progress = (processed / total_domains) * 100
                        self.update_status(f"Processed domain {processed}/{total_domains}", progress
                        )
                        
                    except Exception as e:
                        self.logger.error(f"Error trimming domain {domain_num} of {accession}: {e}")
                        
                # Progress update after each protein
                self.logger.info(f"Completed processing {accession} ({processed}/{total_domains} domains)")


            if not results:
                raise ValidationError("No structures were trimmed successfully")

            # Enhanced summary logging
            self.logger.info(f"PDB Processing Summary:")
            self.logger.info(f"- Found {found_files} PDB files")
            self.logger.info(f"- Missing {missing_files} PDB files")
            self.logger.info(f"- Successfully trimmed {len(results)} domains")

            # Save summary with PDB sources
            self._save_summary(results, pdb_sources)
            return results

        except Exception as e:
            raise ProcessingError(f"PDB trimming failed: {str(e)}")

    def _find_pdb_file(self, pdb_dir: Path, accession: str) -> Optional[Path]:
        """Find PDB file for accession with flexible matching."""
        # Try AlphaFold naming convention first
        alphafold_name = f'AF-{accession}-F1.pdb'
        alphafold_path = pdb_dir / alphafold_name
        
        if alphafold_path.exists():
            if self.validate_structure(alphafold_path):
                return alphafold_path
            else:
                self.logger.warning(f"Found AlphaFold file for {accession} but it appears invalid")
        
        # If custom PDbs are allowed, search for matching files
        if self.config.accept_custom_pdbs:
            matched_files = []
            for path in pdb_dir.glob('*.pdb'):
                matches = False
                if self.config.custom_pdb_strict:
                    # Strict mode: require exact accession match
                    matches = accession in path.stem.split('_')
                else:
                    # Flexible mode: allow partial matches
                    matches = accession in path.name
                    
                if matches:
                    if self.validate_structure(path):
                        matched_files.append(path)
                    else:
                        self.logger.warning(f"Found matching file {path.name} for {accession} but it appears invalid")
            
            if matched_files:
                if len(matched_files) > 1:
                    self.logger.warning(f"Multiple matching PDB files found for {accession}, using first valid match")
                return matched_files[0]
            
        if self.config.accept_custom_pdbs:
            self.logger.info(f"No valid PDB file found for {accession} in custom or AlphaFold format")
        else:
            self.logger.info(f"No valid AlphaFold PDB file found for {accession}")
        
        return None

    def _parse_domain_ranges(self, domain_file: Path) -> Dict[str, List[Tuple[int, int]]]:
        """Parse domain ranges from file"""
        try:
            ranges = {}
            with open(domain_file) as f:
                for line in f:
                    match = self.config.domain_pattern.match(line.strip())
                    if match:
                        accession, start, end = match.groups()
                        if accession not in ranges:
                            ranges[accession] = []
                        ranges[accession].append((int(start), int(end)))
                        
            if not ranges:
                raise ValidationError("No valid domain ranges found in file")
                
            return ranges
            
        except Exception as e:
            raise FileError(f"Failed to parse domain ranges: {e}")

    def _trim_pdb_file(self, input_path: Path, output_path: Path, start: int, end: int):
        """Trim PDB file to specified residue range."""
        try:
            atoms_found = False
            total_atoms = 0
            trimmed_atoms = 0
            
            with open(input_path) as infile, open(output_path, 'w') as outfile:
                for line in infile:
                    if line.startswith('ATOM'):
                        total_atoms += 1
                        try:
                            residue_num = int(line[22:26])
                            if start <= residue_num <= end:
                                outfile.write(line)
                                trimmed_atoms += 1
                                atoms_found = True
                        except ValueError:
                            self.logger.warning(f"Invalid residue number in {input_path.name}")
                            continue
                    elif line.startswith(('TER', 'END')):
                        outfile.write(line)
                
            if not atoms_found:
                raise ValidationError(
                    f"No atoms found in range {start}-{end} in {input_path.name}. "
                    f"Total atoms: {total_atoms}, Valid range atoms: {trimmed_atoms}"
                )
                    
            self.logger.info(
                f"Successfully trimmed {input_path.name}: "
                f"Selected {trimmed_atoms} of {total_atoms} atoms"
            )
                    
        except Exception as e:
            raise FileError(f"Failed to trim PDB file {input_path.name}: {str(e)}")

    def _save_summary(self, results: Dict[str, Path], pdb_sources: Dict[str, str]):
        """Save processing summary with PDB sources.
        
        Args:
            results: Dictionary of trimmed structures
            pdb_sources: Dictionary tracking source of each PDB file
        """
        try:
            summary_path = Path(self.config.output_dir) / "trimming_summary.json"
            
            summary = {
                'version': '1.0',
                'timestamp': datetime.now().isoformat(),
                'total_processed': len(results),
                'pdb_sources': pdb_sources,
                'trimmed_structures': {
                    domain_id: {
                        'path': str(path.relative_to(self.config.output_dir)),
                        'source': pdb_sources[domain_id.split('_')[0]]
                    }
                    for domain_id, path in results.items()
                }
            }
            
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2)
                
        except Exception as e:
            raise FileError(f"Failed to save summary: {e}")

    def validate_structure(self, pdb_path: Path) -> bool:
        """Validate PDB structure file with more comprehensive checks"""
        try:
            with open(pdb_path) as f:
                first_line = f.readline().strip()
                # Check for valid PDB format
                if not (first_line.startswith('ATOM') or first_line.startswith('HEADER')):
                    self.logger.warning(f"File {pdb_path.name} does not appear to be a valid PDB file")
                    return False
                    
                # Check for readable content
                has_content = False
                for line in f:
                    if line.startswith('ATOM'):
                        has_content = True
                        break
                
                if not has_content:
                    self.logger.warning(f"File {pdb_path.name} contains no ATOM records")
                    return False
                    
                return True
        except Exception as e:
            self.logger.error(f"Error validating PDB file {pdb_path.name}: {str(e)}")
            return False
