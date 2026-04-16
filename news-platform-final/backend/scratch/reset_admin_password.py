from app.database import SyncSessionLocal
from app.models.models import AdminUser
from app.services.auth_service import hash_password
from sqlalchemy import select

def reset_admin_password():
    db = SyncSessionLocal()
    try:
        user = db.query(AdminUser).filter(AdminUser.username == "admin").first()
        if user:
            user.password_hash = hash_password("admin123")
            db.commit()
            print("Password for 'admin' has been reset to 'admin123'")
        else:
            print("Admin user not found. Creating 'admin' with password 'admin123'")
            new_user = AdminUser(
                username="admin",
                password_hash=hash_password("admin123"),
                role="admin",
                is_active=True
            )
            db.add(new_user)
            db.commit()
            print("Admin user 'admin' created with password 'admin123'")
    finally:
        db.close()

if __name__ == "__main__":
    reset_admin_password()
