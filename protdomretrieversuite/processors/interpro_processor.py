# protdomretrieversuite/processors/interpro_processor.py
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass
import csv
import json
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
class InterProConfig(ProcessorConfig):
    """InterPro-specific configuration"""
    api_base_url: str = "https://www.ebi.ac.uk/interpro/api"
    page_size: int = 200

class InterProProcessor(BaseProcessor):
    """Handles InterPro domain processing and analysis"""

    @handle_processing_errors
    def process(self, input_file: Path, interpro_entries: List[str]) -> Dict:
        """Process InterPro domains for given entries."""
        if not input_file.exists():
            raise ValidationError(f"Input file not found: {input_file}")
        if not interpro_entries:
            raise ValidationError("No InterPro entries provided")

        accessions = self._read_accessions(input_file)
        self.logger.info(f"Processing {len(accessions)} accessions")
        
        results = {}
        max_domains = [0]  # Using list to track max domains across all proteins
        total = len(accessions)
        
        for i, accession in enumerate(accessions, 1):
            progress = (i / total) * 100
            self.update_status(f"Processing {accession}", progress)
            
            domains = self._get_interpro_data(accession, interpro_entries)
            if domains:
                results[accession] = self._choose_best_domains(domains, accession)
                max_domains[0] = max(max_domains[0], len(results[accession]['domains']))
            
            time.sleep(0.1)  # Rate limiting
        
        self._save_results(results, max_domains[0])
        return results

    def _read_accessions(self, input_file: Path) -> List[str]:
        """Read accessions from input file"""
        try:
            with open(input_file) as f:
                return [line.strip() for line in f if line.strip()]
        except Exception as e:
            raise FileError(f"Failed to read accessions: {e}")

    def _get_interpro_data(self, accession: str, interpro_entries: List[str]) -> Dict[str, List]:
        """Get InterPro domain data for a specific accession"""
        url = f"{self.config.api_base_url}/entry/all/protein/uniprot/{accession}"
        params = {'page_size': self.config.page_size}
        
        for attempt in range(self.config.max_retries):
            try:
                response = requests.get(url, params=params, timeout=self.config.timeout)
                if response.status_code != 200:
                    raise APIError(
                        f"InterPro API error for {accession}",
                        status_code=response.status_code,
                        response=response.json() if 'json' in response.headers.get('content-type', '') else None
                    )
                
                data = response.json()
                domains_by_entry = {}
                
                for entry in data.get('results', []):
                    entry_id = entry['metadata']['accession']
                    if entry_id in interpro_entries:
                        domains_by_entry[entry_id] = []
                        for location in entry['proteins'][0].get('entry_protein_locations', []):
                            for fragment in location.get('fragments', []):
                                start = fragment.get('start')
                                end = fragment.get('end')
                                if start is not None and end is not None:
                                    domains_by_entry[entry_id].append((int(start), int(end)))
                
                return domains_by_entry
                
            except requests.RequestException as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == self.config.max_retries - 1:
                    raise APIError(f"Failed to get InterPro data for {accession} after {self.config.max_retries} attempts")
                time.sleep(2 ** attempt)

    def _choose_best_domains(self, domains_by_entry: Dict[str, List], accession: str) -> Dict:
        """Select the best domains across all entries, taking the longest when there's overlap"""
        # Collect all domains from all entries with their source
        all_domains = []
        entries_by_domain = {}  # Track which entry each domain came from
        
        for entry, domains in domains_by_entry.items():
            for domain in domains:
                all_domains.append(domain)
                entries_by_domain[domain] = entry

        # Sort domains by length (longest first)
        all_domains.sort(key=lambda x: x[1] - x[0], reverse=True)
        
        # Final selected domains and their entries
        selected_domains = []
        temp_domain_map = {}  # (Temp) Map entries to their domain numbers
        domain_counter = 1  # Give each domain a unique number
        
        def domains_overlap(d1, d2):
            return not (d1[1] < d2[0] or d1[0] > d2[1])
        # Select domains using length-priority logic
        for domain in all_domains:
            # Check if this domain overlaps with any selected domain
            overlap = False
            for selected in selected_domains:
                if domains_overlap(domain, selected):
                    overlap = True
                    break
            
            if not overlap:
                selected_domains.append(domain)
                entry = entries_by_domain[domain]
                if entry not in temp_domain_map:
                    temp_domain_map[entry] = []
                # Store the original selection order
                temp_domain_map[entry].append((domain_counter, domain))
                domain_counter += 1
        
        # Reorder selected domains by position
        # Create a list of (domain, original_number) tuples
         
        ordered_domains = [(d, next(num for entry_domains in temp_domain_map.values()
                                    for num, dom in entry_domains if dom == d))
                            for d in selected_domains]
        ordered_domains.sort(key=lambda x: x[0][0])  # Sort by start position
        
        #Create final maps with position-based ordering
        entry_domain_map = {}
        final_domains = []
        domain_positions = {}  # Map original numbers to new positions
        
        for new_idx, (domain, orig_num) in enumerate(ordered_domains, 1):
            final_domains.append(domain)
            entry = entries_by_domain[domain]
            if entry not in entry_domain_map:
                entry_domain_map[entry] = []
            entry_domain_map[entry].append(f"d{new_idx}")
            domain_positions[orig_num] = new_idx
        
        # Format entry string with properly ordered domains
        entry_parts = []
        # Get the first domain position for each entry to determine entry order
        entry_positions = {}
        for entry, domain_info in temp_domain_map.items():
            first_domain = min(domain[0] for domain_counter, domain in domain_info)
            entry_positions[entry] = first_domain
            
        # Sort entries by their first domain position
        sorted_entries = sorted(temp_domain_map.keys(), key=lambda e: entry_positions[e])
        
        for entry in sorted_entries:
            domain_info = temp_domain_map[entry]
            ranges = []
            for orig_num, domain in domain_info:
                new_num = domain_positions[orig_num]
                ranges.append(f"d{new_num}:[{domain[0]},{domain[1]}]")
            ranges.sort(key=lambda x: int(x.split('d')[1].split(':')[0]))  # Sort by new domain number
            entry_parts.append(f"{entry} ({','.join(ranges)})")
        
        entry_string = " + ".join(entry_parts)
        
        # Log domain selection results
        if final_domains:
            self.logger.info(f"Selected domains from entries: {entry_string} in {accession}")
        else:
            self.logger.info(f"No domains found for {accession}")
        
        return {
            'domains': [
                {
                    'entry': entries_by_domain[domain],
                    'start': domain[0],
                    'end': domain[1]
                }
                for domain in final_domains
            ],
            'entry_string': entry_string,
            'entry_map': entry_domain_map
        }

    def _save_results(self, results: Dict, max_domains: int):
        """Save processing results in multiple formats"""
        try:
            output_dir = Path(self.config.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save domain ranges
            ranges_file = output_dir / "domain_ranges.txt"
            with open(ranges_file, 'w') as f:
                for accession, data in results.items():
                    for domain in data['domains']:
                        f.write(f"{accession}[{domain['start']}-{domain['end']}]\n")
            
            # Save detailed TSV results
            tsv_file = output_dir / "domain_analysis.tsv"
            with open(tsv_file, 'w', newline='') as f:
                writer = csv.writer(f, delimiter='\t')
                
                # Write header
                header = ["Protein Accession", "InterPro Entry"]
                for i in range(1, max_domains + 1):
                    header.extend([f"Start {i}", f"End {i}"])
                writer.writerow(header)
                
                # Write data rows
                for accession, data in results.items():
                    row = [accession, data['entry_string']]
                    # Add domain coordinates
                    for domain in data['domains']:
                        row.extend([domain['start'], domain['end']])
                    # Pad with N/A if needed
                    while len(row) < len(header):
                        row.append("N/A")
                    writer.writerow(row)
            
            # Save JSON results for programmatic access
            results_file = output_dir / "interpro_results.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
                
            self.logger.info(f"Results saved to {output_dir}")
                
        except Exception as e:
            self.logger.error(f"Failed to save results: {str(e)}")
            raise FileError(f"Failed to save results: {str(e)}")
