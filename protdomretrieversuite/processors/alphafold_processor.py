# protdomretrieversuite/processors/alphafold_processor.py
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional
import json
import re
import requests
import time

from protdomretrieversuite.processors.base_processor import BaseProcessor, ProcessorConfig
from protdomretrieversuite.utils.errors import (
    handle_processing_errors,
    ProcessingError,
    APIError,
    ValidationError,
    FileError
)

@dataclass
class AlphaFoldConfig(ProcessorConfig):
    """AlphaFold-specific configuration"""
    af_api_url: str = "https://alphafold.ebi.ac.uk/api"
    structures_subdir: str = "alphafold_structures"
    concurrent_downloads: int = 5

class AlphaFoldProcessor(BaseProcessor):
    """Handles AlphaFold structure downloading and processing"""

    @handle_processing_errors
    def process(self, accessions: List[str]) -> Dict[str, Path]:
        """Process and download AlphaFold structures concurrently"""
        if not accessions:
            raise ValidationError("No accessions provided")
            
        self.logger.info(f"Starting AlphaFold downloads for {len(accessions)} accessions")
        
        try:
            structure_dir = Path(self.config.output_dir) / self.config.structures_subdir
            structure_dir.mkdir(parents=True, exist_ok=True)
            
            results = {}
            total = len(accessions)
            processed = 0
            
            # Use ThreadPoolExecutor for concurrent downloads
            with ThreadPoolExecutor(max_workers=self.config.concurrent_downloads) as executor:
                # Submit all download tasks
                future_to_accession = {
                    executor.submit(self._process_single_structure, accession, structure_dir): accession
                    for accession in accessions
                }
                
                # Process completed downloads
                for future in as_completed(future_to_accession):
                    accession = future_to_accession[future]
                    try:
                        result = future.result()
                        if result:
                            results[accession] = result
                            
                        processed += 1
                        progress = (processed / total) * 100
                        self.update_status(f"Processed {processed}/{total} structures", progress)
                        
                    except Exception as e:
                        self.logger.error(f"Error processing {accession}: {e}")
            
            if not results:
                raise ValidationError("No structures were downloaded successfully")
            
            self._save_summary(results)
            self.update_status("AlphaFold processing complete", 100)
            return results
            
        except Exception as e:
            raise ProcessingError(f"AlphaFold processing failed: {e}")

    def _process_single_structure(self, accession: str, structure_dir: Path) -> Optional[Path]:
        """Process a single structure download"""
        try:
            structure_info = self._get_structure_info(accession)
            if structure_info:
                structure_path = self._download_structure(structure_info, structure_dir)
                if structure_path:
                    self.logger.info(f"Downloaded structure for {accession}")
                    return structure_path
            return None
        except Exception as e:
            self.logger.error(f"Failed to process {accession}: {e}")
            return None

    # Helpers and methods
    def _get_structure_info(self, accession: str) -> Dict:
        """Get structure metadata from AlphaFold API"""
        url = f"{self.config.af_api_url}/prediction/{accession}"
        headers = {'accept': 'application/json'}
        
        for attempt in range(self.config.max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=self.config.timeout)
                response.raise_for_status()
                
                entries = response.json()
                if not entries:
                    raise APIError(f"No structure found for {accession}")
                
                entry = entries[0]
                if not entry.get('pdbUrl'):
                    raise APIError(f"No PDB URL for {accession}")
                
                return {
                    'accession': accession,
                    'entry_id': entry['entryId'],
                    'pdb_url': entry['pdbUrl'],
                    'model_date': entry.get('modelDate')
                }
                
            except requests.RequestException as e:
                if attempt == self.config.max_retries - 1:
                    raise APIError(f"Failed to get structure info for {accession}: {e}")
                time.sleep(2 ** attempt)

    def _download_structure(self, structure_info: Dict, output_dir: Path) -> Path:
        """Download structure PDB file"""
        try:
            pdb_url = structure_info['pdb_url']
            output_path = output_dir / f"{structure_info['entry_id']}.pdb"
            
            if output_path.exists():
                if self.validate_structure(output_path):
                    self.logger.info(f"Structure already exists: {output_path}")
                    return output_path
                output_path.unlink()
            
            response = requests.get(pdb_url, timeout=self.config.timeout)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
                
            if not self.validate_structure(output_path):
                raise ValidationError(f"Downloaded structure is invalid: {output_path}")
                
            return output_path
            
        except (requests.RequestException, OSError) as e:
            raise FileError(f"Failed to download structure for {structure_info['accession']}: {e}")

    def _save_summary(self, results: Dict[str, Path]):
        """Save processing summary"""
        try:
            summary_path = Path(self.config.output_dir) / "alphafold_summary.json"
            
            summary = {
                'total_processed': len(results),
                'structures': {
                    accession: str(path.relative_to(self.config.output_dir))
                    for accession, path in results.items()
                }
            }
            
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2)
                
        except Exception as e:
            raise FileError(f"Failed to save summary: {e}")

    def validate_structure(self, pdb_path: Path) -> bool:
        """Validate downloaded structure"""
        try:
            with open(pdb_path) as f:
                first_line = f.readline().strip()
                return first_line.startswith('ATOM') or first_line.startswith('HEADER')
        except Exception:
            return False
