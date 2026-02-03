
from app import app, db
from sqlalchemy import text

with app.app_context():
    try:
        # Check Cart columns
        result = db.session.execute(text("DESCRIBE cart"))
        print("Cart columns:", [row[0] for row in result])
        
        # Check OrderItem columns
        result = db.session.execute(text("DESCRIBE order_items"))
        print("OrderItem columns:", [row[0] for row in result])
        
    except Exception as e:
        print(e)
