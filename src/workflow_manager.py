# src/workflow_manager.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import logging
import threading

from .processors.base_processor import ProcessorConfig
from .processors.interpro_processor import InterProProcessor, InterProConfig
from .processors.fasta_processor import FastaProcessor, FastaConfig
from .processors.alphafold_processor import AlphaFoldProcessor, AlphaFoldConfig
from .processors.pdb_trimmer import PDBTrimmer, PDBTrimmerConfig
from .utils.errors import ProcessingError, ValidationError  # Ensure this import is present


@dataclass
class WorkflowConfig:
    """Configuration for workflow management"""
    output_dir: Path
    pdb_options: Dict[str, bool] = field(default_factory=lambda: {
        'accept_custom_pdbs': False,
        'custom_pdb_strict': False,
        'pdb_source_dir': None
    })
    
class WorkflowManager:
    def __init__(self, output_dir: Path, callback=None, config=None):
        self.output_dir = output_dir
        self.callback = callback
        self.config = WorkflowConfig(
            output_dir=output_dir,
            pdb_options=config if config else {}
        )
        self.results = {}
        self.stop_requested = False
        self._setup_logging()

    def _setup_logging(self):
        self.logger = logging.getLogger(__name__)
    def _generate_summary(self, input_accessions: List[str], interpro_entries: List[str]) -> str:
        """Generate a comprehensive workflow summary.
        
        Args:
            input_accessions: List of initial protein accessions
            interpro_entries: List of InterPro entries used for analysis
        """
        total_proteins = len(input_accessions)
        domains_found = len(self.results.get('domains', {}))
        fasta_count = len(self.results.get('fasta', {}))
        af_count = len(self.results.get('alphafold', {}))
        trimmed_count = len(self.results.get('trimmed', {}))

        summary = [
            "\n=== ProtDomRetriever Analysis Summary ===",
            f"Initial Input: {total_proteins} protein accessions",
            f"InterPro Entries: {', '.join(interpro_entries)}",
            "",
            "Results:",
            f"• Domain Analysis: {domains_found} proteins with matching domains",
            f"• FASTA Sequences: {fasta_count} domain sequences retrieved",
        ]
        # AlphaFold reporting
        if self.config.pdb_options.get('accept_custom_pdbs') and self.config.pdb_options.get('pdb_source_dir'):
            source = f"local directory ({Path(self.config.pdb_options['pdb_source_dir']).name})"
        else:
            source = "AlphaFold database"
            if 'alphafold' in self.results:
                missing_af = total_proteins - af_count
                summary.extend([
                    f"• AlphaFold Structures: {af_count} downloaded",
                    f"  - {missing_af} structures not available in AlphaFold database"
                ])

        # Trimming reporting
        if 'trimmed' in self.results:
            summary.extend([
                f"• Domain-Trimmed Structures: {trimmed_count} generated from {source}",
                f"  - {af_count - trimmed_count if 'alphafold' in self.results else ''} structures could not be trimmed"
            ])

        summary.extend([
            "",
            "Analysis complete! Results are available in the output directory.",
            "=======================================",
        ])

        return "\n".join(summary)

    def run(self, input_file: Path, interpro_entries: List[str],
            retrieve_fasta: bool = False,
            download_alphafold: bool = False,
            trim_pdb: bool = False) -> Dict:
        try:
            # Read input accessions first for summary
            with open(input_file) as f:
                input_accessions = [line.strip() for line in f if line.strip()]

            # Validate inputs
            if not input_file.exists():
                raise ValidationError(f"Input file does not exist: {input_file}")
            if not interpro_entries:
                raise ValidationError("No InterPro entries provided")
        
            # Step 1: InterPro Processing (always required)
            interpro_config = InterProConfig(output_dir=self.output_dir)
            interpro = InterProProcessor(interpro_config, callback=self.callback)
            self.results['domains'] = interpro.process(input_file, interpro_entries)
            self.logger.info(f"Processed domains for {len(self.results['domains'])} proteins")
            
            if self.stop_requested:
                raise ProcessingError("Processing stopped by user")

            # Step 2: FASTA Retrieval (optional)
            if retrieve_fasta:
                fasta_config = FastaConfig(output_dir=self.output_dir)
                fasta = FastaProcessor(fasta_config, callback=self.callback)
                self.results['fasta'] = fasta.process(self.results['domains'])
                fasta_count = len(self.results['fasta']) if self.results.get('fasta') else 0
                self.logger.info(f"Retrieved {fasta_count} FASTA sequences")
                
            if self.stop_requested:
                raise ProcessingError("Processing stopped by user")

            # Step 3: AlphaFold Download (optional)
            if download_alphafold:
                af_config = AlphaFoldConfig(output_dir=self.output_dir)
                af = AlphaFoldProcessor(af_config, callback=self.callback)
                try:
                    self.results['alphafold'] = af.process(list(self.results['domains'].keys()))
                    af_count = len(self.results['alphafold']) if self.results.get('alphafold') else 0
                    self.logger.info(f"Downloaded {af_count} AlphaFold structures")
                except ProcessingError as e:
                    self.logger.warning(f"AlphaFold processing partial or failed: {str(e)}")
                    if not self.results.get('alphafold'):
                        self.logger.warning("No AlphaFold structures were downloaded")
                        if trim_pdb:
                            self.logger.warning("Skipping PDB trimming due to no available structures")
                            return self.results
                
            if self.stop_requested:
                raise ProcessingError("Processing stopped by user")

            # Step 4: PDB Trimming (optional)
            if trim_pdb:
                try:
                    trimmer_config = PDBTrimmerConfig(
                        output_dir=self.output_dir,
                        accept_custom_pdbs=self.config.pdb_options.get('accept_custom_pdbs', False),
                        custom_pdb_strict=self.config.pdb_options.get('custom_pdb_strict', False)
                    )
                    trimmer = PDBTrimmer(trimmer_config, callback=self.callback)
                    domain_ranges = self.output_dir / "domain_ranges.txt"
                    
                    # Check for PDB source
                    if self.config.pdb_options.get('accept_custom_pdbs') and self.config.pdb_options.get('pdb_source_dir'):
                        # User specified a custom PDB directory
                        pdb_dir = Path(self.config.pdb_options['pdb_source_dir'])
                        if not pdb_dir.exists():
                            raise ProcessingError(f"PDB source directory not found: {pdb_dir}")
                        self.logger.info(f"Using custom PDB directory: {pdb_dir}")
                    else:
                        # Use default alphafold_structures directory (whether from download or user-provided)
                        pdb_dir = self.output_dir / "alphafold_structures"
                        if not pdb_dir.exists():
                            raise ProcessingError("No PDB structures available in alphafold_structures directory")
                        self.logger.info("Using structures from alphafold_structures directory")

                    self.results['trimmed'] = trimmer.process(pdb_dir, domain_ranges)
                    trimmed_count = len(self.results['trimmed']) if self.results.get('trimmed') else 0
                    self.logger.info(f"Generated {trimmed_count} trimmed structures")
                except Exception as e:
                    self.logger.error(f"PDB trimming failed: {str(e)}")
                    raise ProcessingError(f"PDB trimming failed: {str(e)}")


            # Generate and log summary at the end
            summary = self._generate_summary(input_accessions, interpro_entries)
            self.logger.info(summary)
            if self.callback:
                self.callback(summary, 100)

            self.logger.info("Workflow completed successfully")
            return self.results

        except ValidationError as e:
            self.logger.error(f"Validation error: {str(e)}")
            raise
        except ProcessingError as e:
            self.logger.error(f"Processing error: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            raise ProcessingError(f"Workflow execution failed: {str(e)}")
