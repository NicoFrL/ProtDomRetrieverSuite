# src/processors/fasta_processor.py
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass
import requests
import time

from .base_processor import BaseProcessor, ProcessorConfig
from ..utils.errors import (
    handle_processing_errors,
    ProcessingError,
    APIError,
    ValidationError,
    FileError
)

@dataclass
class FastaConfig(ProcessorConfig):
    """FASTA processor specific configuration"""
    uniprot_api_url: str = "https://rest.uniprot.org/idmapping"
    job_check_interval: int = 5
    chunk_size: int = 500

class FastaProcessor(BaseProcessor):
    """Handles UniProt FASTA sequence retrieval and processing"""

    @handle_processing_errors
    def process(self, domain_results: Dict) -> Dict:
        """
        Retrieve and process FASTA sequences for domains.
        
        Args:
            domain_results: Dictionary of domain results from InterPro processor
            
        Returns:
            Dict containing domain sequences
            
        Raises:
            ValidationError: If domain_results is empty
            APIError: If API communication fails
            FileError: If file operations fail
        """
        if not domain_results:
            raise ValidationError("No domain results provided")
            
        # Get unique accessions
        accessions = list(domain_results.keys())
        self.update_status("Submitting UniProt job", 0)
        
        # Step 1: Submit ID mapping job
        job_id = self._submit_uniprot_job(accessions)
        
        # Step 2: Monitor job status
        self.update_status("Waiting for UniProt job completion", 20)
        if not self._check_job_status(job_id):
            raise APIError("UniProt job failed or timed out")
        
        # Step 3: Get FASTA sequences
        self.update_status("Retrieving FASTA sequences", 40)
        fasta_content = self._get_job_results(job_id)
        if not fasta_content:
            raise APIError("Failed to retrieve FASTA sequences")
        
        # Step 4: Process sequences and extract domains
        self.update_status("Processing domain sequences", 60)
        domain_sequences = self._extract_domain_sequences(fasta_content, domain_results)
        
        # Step 5: Save results
        self.update_status("Saving results", 80)
        self._save_results(domain_sequences)
        
        self.update_status("FASTA processing complete", 100)
        return domain_sequences

    def _submit_uniprot_job(self, accessions: List[str]) -> str:
        """Submit ID mapping job to UniProt"""
        url = f"{self.config.uniprot_api_url}/run"
        data = {
            'ids': ','.join(accessions),
            'from': "UniProtKB_AC-ID",
            'to': "UniProtKB"
        }
        
        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
            return response.json()['jobId']
        except requests.RequestException as e:
            raise APIError(f"Failed to submit UniProt job: {e}")

    def _check_job_status(self, job_id: str) -> bool:
        """Monitor UniProt job status"""
        check_url = f"{self.config.uniprot_api_url}/status/{job_id}"
        start_time = time.time()
        
        while True:
            try:
                response = requests.get(check_url)
                response.raise_for_status()
                status = response.json()
                
                if 'jobStatus' in status:
                    if status['jobStatus'] == "FINISHED":
                        return True
                elif 'results' in status or 'failedIds' in status:
                    return True

                if time.time() - start_time > self.config.timeout:
                    raise APIError(f"Job timed out after {self.config.timeout} seconds")
                
                # Update progress periodically
                elapsed = time.time() - start_time
                progress = min(95, (elapsed / self.config.timeout) * 100)
                self.update_status(f"Waiting for job completion ({int(elapsed)}s)", 20 + progress * 0.2)
                
                time.sleep(self.config.job_check_interval)
                
            except requests.RequestException as e:
                raise APIError(f"Error checking job status: {e}")

    def _get_job_results(self, job_id: str) -> str:
        """Retrieve results from completed UniProt job"""
        try:
            details_url = f"{self.config.uniprot_api_url}/details/{job_id}"
            response = requests.get(details_url)
            response.raise_for_status()
            details = response.json()
            
            if 'redirectURL' not in details:
                raise APIError("No redirect URL in job details")
            
            results_url = details['redirectURL']
            params = {
                'format': 'fasta',
                'size': self.config.chunk_size
            }
            
            # Get all pages of results
            all_results = []
            page = 1
            
            while True:
                response = requests.get(results_url, params=params)
                response.raise_for_status()
                
                content = response.text
                if not content.strip():
                    break
                
                all_results.append(content)
                self.update_status(f"Retrieved page {page} of results", 40 + page)
                
                # Check for next page
                if 'Link' in response.headers:
                    next_link = [link.strip() for link in response.headers['Link'].split(',')
                               if 'next' in link]
                    if next_link:
                        results_url = next_link[0].split(';')[0].strip('<>')
                        page += 1
                    else:
                        break
                else:
                    break
            
            if not all_results:
                raise APIError("No FASTA sequences retrieved")
                
            return '\n'.join(all_results)
            
        except requests.RequestException as e:
            raise APIError(f"Failed to get job results: {e}")

    def _extract_domain_sequences(self, fasta_content: str, domain_results: Dict) -> Dict:
        """Extract domain sequences from FASTA content"""
        try:
            sequences = {}
            current_accession = None
            current_sequence = ""
            
            # Parse FASTA content
            for line in fasta_content.split('\n'):
                if line.startswith('>'):
                    if current_accession:
                        sequences[current_accession] = current_sequence
                    current_accession = line.split('|')[1]
                    current_sequence = ""
                else:
                    current_sequence += line.strip()
            
            if current_accession:
                sequences[current_accession] = current_sequence
            
            # Extract domain sequences
            domain_sequences = {}
            total = sum(len(data['domains']) for data in domain_results.values())
            processed = 0
            
            for accession, data in domain_results.items():
                if accession in sequences:
                    for domain in data['domains']:
                        try:
                            start = domain['start']
                            end = domain['end']
                            domain_key = f"{accession}[{start}-{end}]"
                            
                            domain_sequences[domain_key] = {
                                'sequence': sequences[accession][start-1:end],
                                'entry': domain['entry'],
                                'accession': accession,
                                'start': start,
                                'end': end
                            }
                            
                            processed += 1
                            progress = (processed / total) * 100
                            self.update_status(f"Processed domain {processed}/{total}", 60 + progress * 0.2)
                            
                        except IndexError:
                            self.logger.warning(f"Invalid domain range for {accession}: {start}-{end}")
                else:
                    self.logger.warning(f"No sequence found for accession {accession}")
            
            if not domain_sequences:
                raise ValidationError("No valid domain sequences extracted")
                
            return domain_sequences
            
        except Exception as e:
            raise ValidationError(f"Failed to extract domain sequences: {str(e)}")

    def _save_results(self, domain_sequences: Dict):
        """Save domain sequences to FASTA file"""
        try:
            output_dir = Path(self.config.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            fasta_file = output_dir / "domain_sequences.fasta"
            with open(fasta_file, 'w') as f:
                for domain_key, info in domain_sequences.items():
                    header = f">{domain_key} {info['entry']}"
                    f.write(f"{header}\n{info['sequence']}\n")

            self.logger.info(f"Saved {len(domain_sequences)} domain sequences to {fasta_file}")
            
        except Exception as e:
            raise FileError(f"Failed to save FASTA results: {e}")
