import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cafe import create_app
from cafe.db import db
app = create_app()
with app.app_context():
    assert db().execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    print('Schema:', db().execute('SELECT max(version) FROM schema_version').fetchone()[0])
    for name in ['uploads', 'logs', 'backups']:
        with tempfile.TemporaryFile(dir=Path(app.config['DATA_DIR']) / name) as f:
            f.write(b'check')
    print('Data directories writable. Import and database OK.')
