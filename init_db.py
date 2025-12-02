from app import app, db, User, Unit, AgentCode

# Initialize database inside Flask app context
with app.app_context():
    db.create_all()

    # OPTIONAL: Insert sample agent codes
    if not AgentCode.query.first():
        sample_codes = ["123456", "654321", "111222"]
        for code in sample_codes:
            db.session.add(AgentCode(code=code))
        db.session.commit()
        print("Sample agent codes inserted.")

    # OPTIONAL: Insert sample units
    if not Unit.query.first():
        sample_units = [
            Unit(name="Unit A1", status="available", polygon="[]", base_price=1500000),
            Unit(name="Unit A2", status="reserved", polygon="[]", base_price=1550000),
            Unit(name="Unit A3", status="sold", polygon="[]", base_price=1600000),
        ]
        db.session.add_all(sample_units)
        db.session.commit()
        print("Sample units inserted.")

    print("Database initialized successfully.")
