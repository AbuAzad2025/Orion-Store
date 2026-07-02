import os
import sys
from pathlib import Path

ROOT = Path('D:/Data/Orion-SAAS Store').resolve()
for sub in ('02-CORE', '03-MODELS', '04-SERVICES', '05-API'):
    sys.path.insert(0, str(ROOT / sub))

from user.user import User
from orion.app import create_app
from auth.auth_service import AuthService
from platform_svc.platform_settings_service import PlatformSettingsService

os.environ.setdefault('FLASK_ENV', 'development')
os.environ.setdefault('DATABASE_URL', 'postgresql://azadexa:azadexa_dev@localhost:5432/azadexa_dev')
app = create_app()

with app.app_context():
    if User.query.filter_by(tenant_id=None).first():
        print('ERROR: Platform admin already exists. Cannot bootstrap.')
        sys.exit(1)
        
    import getpass
    email = input('Platform admin email: ').strip().lower()
    password = getpass.getpass('Password (min 8 chars): ')
    if len(password) < 8:
        print('ERROR: Password must be at least 8 characters.')
        sys.exit(1)
        
    PlatformSettingsService().ensure_seeded()
    auth = AuthService()
    user = auth.register_super_admin(email=email, password=password, first_name='Platform')
    print(f'SUCCESS: Platform admin created with email: {user.email}')
