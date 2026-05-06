"""
Phase 3: Load Clean Data into Django Models

This script:
- Reads clean CSV files from data/clean/
- Creates Company and StockPrice objects
- Loads data into SQLite database
"""

import os
import sys
import django
from pathlib import Path
import pandas as pd

# Setup Django - resolve paths relative to this script
SCRIPT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPT_DIR / "api"))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nifty100_project.settings')
django.setup()

from core.models import Company, StockPrice

CLEAN_DATA_DIR = SCRIPT_DIR / "data" / "clean"

def load_data():
    """
    Main function to load clean data into database
    """
    csv_files = list(CLEAN_DATA_DIR.glob('*.csv'))
    
    if not csv_files:
        print(f"No CSV files found in {CLEAN_DATA_DIR}")
        return
    
    for csv_file in csv_files:
        if csv_file.name == 'metrics.csv':
            continue
        
        try:
            company_ticker = csv_file.stem.upper()
            
            # Create or get company
            company, created = Company.objects.get_or_create(
                ticker=company_ticker,
                defaults={
                    'company_name': company_ticker,
                    'sector': 'IT' if company_ticker in ['TCS', 'INFY'] else 'Finance'
                }
            )
            
            if created:
                print(f"  OK Company: {company_ticker}")
            
            # Read CSV
            df = pd.read_csv(csv_file)
            df.columns = df.columns.str.lower().str.strip()
            
            # Load stock prices
            loaded_count = 0
            for _, row in df.iterrows():
                obj, created = StockPrice.objects.get_or_create(
                    company=company,
                    date=pd.to_datetime(row['date']).date(),
                    defaults={
                        'open_price': float(row.get('open', 0)),
                        'high_price': float(row.get('high', 0)),
                        'low_price': float(row.get('low', 0)),
                        'close_price': float(row.get('close', 0)),
                        'volume': int(row.get('volume', 0))
                    }
                )
                if created:
                    loaded_count += 1
            
            print(f"  OK {company_ticker}: {loaded_count} new price records loaded")
        
        except Exception as e:
            print(f"  FAIL {csv_file.name}: {str(e)}")

if __name__ == "__main__":
    load_data()
    print("Data loading complete.")
