from app import app, db, Admin

with app.app_context():
    admin = Admin(
        username="admin",
        is_admin=True
    )
    admin.set_password("admin123")

    db.session.add(admin)
    db.session.commit()

    print("Admin created successfully")
