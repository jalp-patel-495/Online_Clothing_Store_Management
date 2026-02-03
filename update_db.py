
from app import app, db
from sqlalchemy import text

with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE cart ADD COLUMN size VARCHAR(20) DEFAULT NULL"))
        print("Added size column to cart")
    except Exception as e:
        print(f"Cart update error (maybe exists): {e}")

    try:
        db.session.execute(text("ALTER TABLE order_items ADD COLUMN size VARCHAR(20) DEFAULT NULL"))
        print("Added size column to order_items")
    except Exception as e:
        print(f"OrderItem update error (maybe exists): {e}")
        
    db.session.commit()
