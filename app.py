from flask import Flask, request, render_template, jsonify
from datetime import datetime
import re
import pandas as pd

app = Flask(__name__)

class TransactionAnalyzer:
    def __init__(self):
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
        # Extract basic statement information
        statement_date = re.search(r'Statement Date:(\d{2}/\d{2}/\d{4})', text)
        payment_due_date = re.search(r'Payment Due Date\s+(\d{2}/\d{2}/\d{4})', text)
        total_dues = re.search(r'Total Dues\s+([\d,]+\.\d{2})', text)
        
        # Parse transactions
        transactions = []
        
        # Regular expression for matching transaction lines
        transaction_pattern = r'(\d{2}/\d{2}/\d{4})\s+(?:\d{2}:\d{2}:\d{2})?\s+([^0-9]+?)\s+(?:(\d+)\s+)?([0-9,.]+(?:\s+Cr)?)'
        
        matches = re.finditer(transaction_pattern, text)
        
        for match in matches:
            date, description, points, amount = match.groups()
            
            # Clean up amount
            amount = amount.strip()
            is_credit = 'Cr' in amount
            amount = float(amount.replace('Cr', '').replace(',', ''))
            if is_credit:
                amount = -amount  # Make credits negative
                
            transaction = {
                'date': datetime.strptime(date, '%d/%m/%Y'),
                'description': description.strip(),
                'points': int(points) if points else 0,
                'amount': amount,
                'category': self.categorize_transaction(description.strip())
            }
            transactions.append(transaction)
        
        return {
            'statement_date': statement_date.group(1) if statement_date else None,
            'payment_due_date': payment_due_date.group(1) if payment_due_date else None,
            'total_dues': float(total_dues.group(1).replace(',', '')) if total_dues else None,
            'transactions': transactions
        }
    
    def categorize_transaction(self, description):
        for category, keywords in self.categories.items():
            if any(keyword.upper() in description.upper() for keyword in keywords):
                return category
        return 'OTHERS'
    
    def analyze_spending(self, transactions):
        df = pd.DataFrame(transactions)
        
        # Category-wise analysis
        category_spending = df.groupby('category')['amount'].agg([
            ('total', 'sum'),
            ('count', 'count'),
            ('average', 'mean')
        ]).round(2)
        
        # Daily spending
        daily_spending = df.groupby(df['date'].dt.date)['amount'].sum()
        
        # Points earned
        total_points = df['points'].sum()
        
        # International vs Domestic
        international = df[df['description'].str.contains('CAD|GBP|USD|EUR', case=False, na=False)]
        domestic = df[~df['description'].str.contains('CAD|GBP|USD|EUR', case=False, na=False)]
        
        return {
            'category_spending': category_spending.to_dict('index'),
            'daily_spending': daily_spending.to_dict(),
            'total_points': total_points,
            'international_spend': international['amount'].sum(),
            'domestic_spend': domestic['amount'].sum(),
            'largest_transaction': df.loc[df['amount'].idxmax()].to_dict() if not df.empty else None,
            'transaction_count': len(df)
        }

@app.route('/')
def home():
    return render_template('Git/karanversation/xa-adv/upload.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'statement' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['statement']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    statement_text = file.read().decode('utf-8')
    analyzer = TransactionAnalyzer()
    
    try:
        parsed_data = analyzer.parse_statement(statement_text)
        analysis = analyzer.analyze_spending(parsed_data['transactions'])
        
        return jsonify({
            'statement_info': {
                'statement_date': parsed_data['statement_date'],
                'payment_due_date': parsed_data['payment_due_date'],
                'total_dues': parsed_data['total_dues']
            },
            'analysis': analysis
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
