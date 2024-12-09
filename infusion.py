from typing import List, Dict
from datetime import datetime

def resolve_cpt_codes(medications: List[Dict], extracted_codes: List[str]) -> List[str]:
    """
    Resolve CPT code conflicts and apply replacement rules
    
    Args:
        medications: List of medication administration records
        extracted_codes: List of CPT codes initially extracted by GPT
    
    Returns:
        List of final CPT codes after applying all rules
    """
    
    # Define CPT code hierarchies and rules
    cpt_rules = {
        # Initial codes hierarchy (higher number = higher priority)
        'initial_hierarchy': {
            '96413': 4,  # Chemo initial
            '96365': 3,  # Therapeutic initial
            '96374': 2,  # IV Push initial
            '96360': 1,  # Hydration initial
        },
        
        # Additional/subsequent codes mapping
        'additional_codes': {
            '96413': '96415',  # Chemo additional
            '96365': '96366',  # Therapeutic additional
            '96374': '96375',  # IV Push subsequent
            '96360': '96361',  # Hydration additional
        },
        
        # Codes that cannot coexist
        'mutually_exclusive': {
            '96365': ['96360'],  # Therapeutic excludes hydration
            '96413': ['96360'],  # Chemo excludes hydration
            '96374': ['96375']   # Initial push excludes subsequent in same time
        },
        
        # Codes that require specific timing
        'time_requirements': {
            '96374': 15,  # IV Push must be < 15 mins
            '96375': 15,  # Subsequent push must be < 15 mins
            '96365': 15,  # Therapeutic must be >= 15 mins
            '96413': 15,  # Chemo must be >= 15 mins
            '96360': 30   # Hydration must be >= 30 mins
        }
    }

    def get_duration(med: Dict) -> float:
        """Calculate duration in minutes for a medication"""
        start = datetime.strptime(med['start_datetime'], '%Y-%m-%d %H:%M:%S')
        stop = datetime.strptime(med['stop_datetime'], '%Y-%m-%d %H:%M:%S')
        return (stop - start).total_seconds() / 60

    def should_remove_code(code: str, all_codes: List[str], med_duration: float) -> bool:
        """Check if a code should be removed based on rules"""
        # Check time requirements
        if code in cpt_rules['time_requirements']:
            required_time = cpt_rules['time_requirements'][code]
            if code in ['96374', '96375']:  # Push codes
                if med_duration >= required_time:
                    return True
            else:  # Infusion codes
                if med_duration < required_time:
                    return True
        
        # Check mutual exclusivity
        if code in cpt_rules['mutually_exclusive']:
            excluded_codes = cpt_rules['mutually_exclusive'][code]
            if any(exc in all_codes for exc in excluded_codes):
                return True
        
        # Check hierarchy (remove lower priority initials if higher exists)
        if code in cpt_rules['initial_hierarchy']:
            current_priority = cpt_rules['initial_hierarchy'][code]
            for other_code in all_codes:
                if other_code in cpt_rules['initial_hierarchy']:
                    if cpt_rules['initial_hierarchy'][other_code] > current_priority:
                        return True
        
        return False

    def handle_push_sequence(codes: List[str], med_times: List[datetime]) -> List[str]:
        """Handle IV push sequence codes (96374 -> 96375)"""
        if '96374' not in codes:
            return codes
        
        result = []
        found_first_push = False
        
        # Sort codes by medication time
        code_times = list(zip(codes, med_times))
        code_times.sort(key=lambda x: x[1])
        
        for code, _ in code_times:
            if code == '96374':
                if not found_first_push:
                    result.append('96374')
                    found_first_push = True
                else:
                    result.append('96375')  # Convert subsequent pushes to 96375
            else:
                result.append(code)
        
        return result

    # Main processing
    final_codes = set()
    med_times = []
    
    # First pass: Collect valid codes based on time requirements
    for med in medications:
        duration = get_duration(med)
        med_codes = [code for code in extracted_codes if not should_remove_code(code, extracted_codes, duration)]
        final_codes.update(med_codes)
        if med_codes:
            med_times.append(datetime.strptime(med['start_datetime'], '%Y-%m-%d %H:%M:%S'))
    
    # Convert to list and handle push sequences
    final_codes = list(final_codes)
    if med_times:
        final_codes = handle_push_sequence(final_codes, med_times)
    
    # Sort based on hierarchy
    def get_code_priority(code: str) -> int:
        if code in cpt_rules['initial_hierarchy']:
            return -cpt_rules['initial_hierarchy'][code]  # Negative for reverse sort
        if code in cpt_rules['additional_codes'].values():
            return 0
        return 1
    
    final_codes.sort(key=get_code_priority)
    
    return final_codes

# Example usage
if __name__ == "__main__":
    # Example data
    medications = [
        {
            'med_name': 'Push Med 1',
            'start_datetime': '2024-01-01 10:00:00',
            'stop_datetime': '2024-01-01 10:05:00',
        },
        {
            'med_name': 'Push Med 2',
            'start_datetime': '2024-01-01 10:10:00',
            'stop_datetime': '2024-01-01 10:14:00',
        },
        {
            'med_name': 'Hydration',
            'start_datetime': '2024-01-01 10:15:00',
            'stop_datetime': '2024-01-01 11:30:00',
        }
    ]
    
    # Example extracted codes
    extracted_codes = ['96374', '96374', '96360', '96361']
    
    final_codes = resolve_cpt_codes(medications, extracted_codes)
    print("Final CPT Codes:", final_codes)
