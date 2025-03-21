import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_key")

# Authentication removed

# Never remove the database to ensure bill persistence
sqlite_path = "instance/bills.db"
# Always preserve the database - removed the code that deletes it

# Use a persistent database path for deployment
# Update the database configuration section
if os.environ.get("RENDER") == "1":
    # In Render deployment, use the specified data directory
    os.makedirs("/data", exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////data/bills.db"
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///bills.db")

# Remove or comment out Replit specific code
# if os.environ.get("REPLIT_DEPLOYMENT") != "1":
#     os.environ["REPLIT_DEPLOYMENT"] = "0"

# Restore data from Replit DB if SQLite is empty
def restore_from_replit_db():
    try:
        from models import Bill
        from replit import db
        import json
        from datetime import datetime

        # Only restore if there are no bills in SQLite but there are in Replit DB
        if Bill.query.count() == 0:
            try:
                bill_keys = [k for k in db.keys() if k.startswith('bill_')]
                if bill_keys:
                    for key in bill_keys:
                        bill_data = db[key]
                        # Create Bill object from Replit DB data
                        new_bill = Bill(
                            bill_number=bill_data['bill_number'],
                            client_name=bill_data['client_name'],
                            phone_number=bill_data['phone_number'],
                            date=datetime.fromisoformat(bill_data['date']),
                            items=bill_data['items'],
                            subtotal=bill_data['subtotal'],
                            total=bill_data['total'],
                            pdf_path=bill_data['pdf_path'],
                            amount_paid=bill_data['amount_paid'],
                            payment_status=bill_data['payment_status']
                        )
                        db.session.add(new_bill)
                    db.session.commit()
                    print(f"Successfully restored {len(bill_keys)} bills from Replit DB")
            except Exception as e:
                print(f"Error restoring from Replit DB: {str(e)}")
                # Continue without Replit DB if there's an error
    except ImportError:
        print("Replit DB module not available")
        # Continue without Replit DB if it's not available
    except Exception as e:
        print(f"Error in restore_from_replit_db: {str(e)}")
        # Continue without Replit DB if there's an error

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

from routes import *  # noqa: F401

def create_tables():
    with app.app_context():
        db.create_all()

        # Make sure we migrate to add the new table
        try:
            from models import PaymentHistory
            # Check if the PaymentHistory table exists
            PaymentHistory.query.first()
        except Exception as e:
            app.logger.info("Creating PaymentHistory table")
            db.create_all()

with app.app_context():
    create_tables()
    restore_from_replit_db()

# At the top of your app.py, after the imports
import traceback

# Add this error handler
@app.errorhandler(500)
def internal_error(error):
    app.logger.error('Server Error: %s', str(error))
    app.logger.error('Traceback: %s', traceback.format_exc())
    return "Internal Server Error", 500

@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error('Unhandled Exception: %s', str(e))
    app.logger.error('Traceback: %s', traceback.format_exc())
    return "Internal Server Error", 500