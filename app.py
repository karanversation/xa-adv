from flask import Flask, request, render_template, jsonify
from datetime import datetime
import re
import pandas as pd
import glog as log
import os

app = Flask(__name__)

# Initialize glog at startup
log.setLevel("INFO")
log.info("Credit Card Analyzer startup")

class TransactionAnalyzer:
    # ... [previous TransactionAnalyzer code remains the same] ...

@app.route('/')
def home():
    log.info('Accessing home page')
    try:
        log.debug(f'Current directory: {os.getcwd()}')
        log.debug(f'Templates directory exists: {os.path.exists("templates")}')
        if os.path.exists("templates"):
            log.debug(f'Templates directory contents: {os.listdir("templates")}')
        return render_template('upload.html')
    except Exception as e:
        log.error(f'Error rendering template: {str(e)}')
        log.exception('Full traceback:')
        return f"Error: {str(e)}", 500

@app.route('/analyze', methods=['POST'])
def analyze():
    log.info('Received analyze request')
    
    if 'statement' not in request.files:
        log.warning('No file uploaded')
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['statement']
    if file.filename == '':
        log.warning('No file selected')
        return jsonify({'error': 'No file selected'}), 400
    
    log.info(f'Processing file: {file.filename}')
    
    try:
        statement_text = file.read().decode('utf-8')
        analyzer = TransactionAnalyzer()
        
        log.info('Parsing statement')
        parsed_data = analyzer.parse_statement(statement_text)
        
        log.info('Analyzing spending')
        analysis = analyzer.analyze_spending(parsed_data['transactions'])
        
        log.info('Analysis complete')
        return jsonify({
            'statement_info': {
                'statement_date': parsed_data['statement_date'],
                'payment_due_date': parsed_data['payment_due_date'],
                'total_dues': parsed_data['total_dues']
            },
            'analysis': analysis
        })
    except Exception as e:
        log.error(f'Error during analysis: {str(e)}')
        log.exception('Full traceback:')
        return jsonify({'error': str(e)}), 500

class TransactionAnalyzer:
    def __init__(self):
        log.info('Initializing TransactionAnalyzer')
        self.categories = {
            'FOOD_DELIVERY': ['ZOMATO', 'BLINKIT'],
            'TRANSPORT': ['UBER', 'OLACABS'],
            'SHOPPING': ['WESTSIDE', 'FLIPKART', 'VIP', 'MY APPARELS'],
            'TRAVEL': ['AIR CANADA', 'MAKEMYTRIP', 'HUDSON NEWS', 'WDF', 'ENCALM LOUNGE'],
            'TELECOM': ['RELIANCE JIO', 'AIRTE'],
            'DINING': ['CARNATIC CAFE', 'DLF MALL OF INDIA FOOD', 'DINEOUT'],
            'FUEL': ['PETRO'],
            'OTHERS': []
        }
    
    def parse_statement(self, text):
        log.info('Starting statement parsing')
        # Extract basic statement information
        statement_date = re.search(r'Statement Date:(\d{2}/\d{2}/\d{4})', text)
        payment_due_date = re.search(r'Payment Due Date\s+(\d{2}/\d{2}/\d{4})', text)
        total_dues = re.search(r'Total Dues\s+([\d,]+\.\d{2})', text)
        
        log.debug(f'Found statement date: {statement_date.group(1) if statement_date else "Not found"}')
        log.debug(f'Found payment due date: {payment_due_date.group(1) if payment_due_date else "Not found"}')
        
        # Parse transactions
        transactions = []
        transaction_pattern = r'(\d{2}/\d{2}/\d{4})\s+(?:\d{2}:\d{2}:\d{2})?\s+([^0-9]+?)\s+(?:(\d+)\s+)?([0-9,.]+(?:\s+Cr)?)'
        
        matches = re.finditer(transaction_pattern, text)
        
        for match in matches:
            date, description, points, amount = match.groups()
            
            amount = amount.strip()
            is_credit = 'Cr' in amount
            amount = float(amount.replace('Cr', '').replace(',', ''))
            if is_credit:
                amount = -amount
                
            transaction = {
                'date': datetime.strptime(date, '%d/%m/%Y'),
                'description': description.strip(),
                'points': int(points) if points else 0,
                'amount': amount,
                'category': self.categorize_transaction(description.strip())
            }
            transactions.append(transaction)
            log.debug(f'Parsed transaction: {transaction["date"]} - {transaction["description"]} - {transaction["amount"]}')
        
        log.info(f'Finished parsing {len(transactions)} transactions')
        return {
            'statement_date': statement_date.group(1) if statement_date else None,
            'payment_due_date': payment_due_date.group(1) if payment_due_date else None,
            'total_dues': float(total_dues.group(1).replace(',', '')) if total_dues else None,
            'transactions': transactions
        }
    
    def categorize_transaction(self, description):
        for category, keywords in self.categories.items():
            if any(keyword.upper() in description.upper() for keyword in keywords):
                log.debug(f'Categorized "{description}" as {category}')
                return category
        log.debug(f'Categorized "{description}" as OTHERS')
        return 'OTHERS'
    
    def analyze_spending(self, transactions):
        log.info('Starting spending analysis')
        df = pd.DataFrame(transactions)
        
        # Category-wise analysis
        category_spending = df.groupby('category')['amount'].agg([
            ('total', 'sum'),
            ('count', 'count'),
            ('average', 'mean')
        ]).round(2)
        
        log.debug('Category-wise spending calculated')
        
        # Daily spending
        daily_spending = df.groupby(df['date'].dt.date)['amount'].sum()
        log.debug('Daily spending calculated')
        
        # Points earned
        total_points = df['points'].sum()
        log.debug(f'Total points calculated: {total_points}')
        
        # International vs Domestic
        international = df[df['description'].str.contains('CAD|GBP|USD|EUR', case=False, na=False)]
        domestic = df[~df['description'].str.contains('CAD|GBP|USD|EUR', case=False, na=False)]
        
        analysis_result = {
            'category_spending': category_spending.to_dict('index'),
            'daily_spending': daily_spending.to_dict(),
            'total_points': total_points,
            'international_spend': international['amount'].sum(),
            'domestic_spend': domestic['amount'].sum(),
            'largest_transaction': df.loc[df['amount'].idxmax()].to_dict() if not df.empty else None,
            'transaction_count': len(df)
        }
        
        log.info('Finished spending analysis')
        return analysis_result

if __name__ == '__main__':
    log.info('Starting Flask application')
    app.run(debug=True)
