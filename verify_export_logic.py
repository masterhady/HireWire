import datetime

# Mock the class and method
class MockView:
    def _calculate_solved_count(self, stats, filter_month, filter_year):
        if not stats:
            return 0
            
        default_solved = stats.get('total_solved', 0)
        
        if filter_month == 'all' and filter_year == 'all':
            return default_solved
            
        submission_calendar = stats.get('submission_calendar')
        if not submission_calendar:
            return default_solved
            
        try:
            target_month = int(filter_month) if filter_month != 'all' else None
            target_year = int(filter_year) if filter_year != 'all' else None
            count = 0
            
            for ts, val in submission_calendar.items():
                try:
                    dt = datetime.datetime.fromtimestamp(int(ts))
                    month_match = True
                    year_match = True
                    
                    if target_month is not None:
                        month_match = dt.month == target_month
                        
                    if target_year is not None:
                        year_match = dt.year == target_year
                        
                    if month_match and year_match:
                        count += val
                except:
                    continue
                    
            return count
        except:
            return default_solved

view = MockView()

# Test Data
stats = {
    'total_solved': 100,
    'submission_calendar': {
        "1733011200": 10, # Dec 1, 2024
        "1733097600": 5,  # Dec 2, 2024
        "1701388800": 3   # Dec 1, 2023
    }
}

# Test Cases
print(f"No Filter: {view._calculate_solved_count(stats, 'all', 'all')} (Expected: 100)")
print(f"Dec 2024: {view._calculate_solved_count(stats, '12', '2024')} (Expected: 15)")
print(f"Dec All Years: {view._calculate_solved_count(stats, '12', 'all')} (Expected: 18)")
print(f"2024 All Months: {view._calculate_solved_count(stats, 'all', '2024')} (Expected: 15)")
