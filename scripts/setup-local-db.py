"""Prepare the project's isolated PostgreSQL demo cluster on Windows."""
import os
from pathlib import Path
import secrets
import subprocess
from urllib.parse import urlparse

import psycopg
from psycopg import sql
from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parent.parent
LOCAL = ROOT / '.local'
BIN = LOCAL / 'postgresql-win' / 'pgsql' / 'bin'
DATA = LOCAL / 'pgdata'
PORT = 55432


def run(*args):
    subprocess.run([str(arg) for arg in args], check=True, cwd=ROOT)


def main():
    if os.name != 'nt':
        raise SystemExit('Este preparo portátil é para Windows. Use o compose.yaml nos demais ambientes.')
    if not (BIN / 'initdb.exe').is_file():
        raise SystemExit('Extraia os binários PostgreSQL em .local/postgresql-win conforme o README.')
    LOCAL.mkdir(exist_ok=True)
    env_path = ROOT / '.env'
    if not env_path.exists():
        password = secrets.token_hex(24)
        env_path.write_text(
            'DEBUG=true\nDEMO_MODE=true\n'
            f'SECRET_KEY={secrets.token_urlsafe(48)}\n'
            'ALLOWED_HOSTS=localhost,127.0.0.1\n'
            f'DATABASE_URL=postgresql://movi:{password}@127.0.0.1:{PORT}/movi_demo\n'
            'CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173\n'
            'BUSINESS_APPROVALS=\nATTENDANCE_POLICY=\n', encoding='utf-8',
        )
    env = dotenv_values(env_path)
    database = urlparse(env.get('DATABASE_URL', ''))
    if (database.scheme != 'postgresql' or database.hostname != '127.0.0.1'
            or database.port != PORT or database.path != '/movi_demo'
            or database.username != 'movi' or not database.password
            or env.get('DEBUG') != 'true' or env.get('DEMO_MODE') != 'true'):
        raise SystemExit('.env existente não corresponde ao banco portátil de demonstração. Use o preparo manual do README.')
    if not (DATA / 'PG_VERSION').exists():
        password_file = LOCAL / 'initdb-password.tmp'
        password_file.write_text(database.password, encoding='utf-8')
        try:
            run(BIN / 'initdb.exe', '-D', DATA, '-U', 'movi', '--encoding=UTF8', '--locale=C',
                '--auth=scram-sha-256', f'--pwfile={password_file}')
        finally:
            password_file.unlink(missing_ok=True)
    status = subprocess.run([str(BIN / 'pg_ctl.exe'), '-D', str(DATA), 'status'], capture_output=True)
    if status.returncode != 0:
        run(BIN / 'pg_ctl.exe', '-D', DATA, '-l', LOCAL / 'postgres.log',
            '-o', f'-p {PORT} -h 127.0.0.1', '-w', 'start')
    with psycopg.connect(host='127.0.0.1', port=PORT, user='movi', password=database.password,
                         dbname='postgres', autocommit=True, connect_timeout=5) as connection:
        # Check the server identity before creating either database.
        actual_data = connection.execute('SHOW data_directory').fetchone()[0]
        if Path(actual_data).resolve() != DATA.resolve():
            raise SystemExit('A porta aponta para outro cluster PostgreSQL. Nenhum banco foi criado.')
        for name in ('movi_demo', 'movi_e2e'):
            if not connection.execute('SELECT 1 FROM pg_database WHERE datname = %s', (name,)).fetchone():
                connection.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    e2e_path = ROOT / '.env.e2e'
    if not e2e_path.exists():
        e2e_path.write_text(
            f'E2E_DATABASE_URL=postgresql://movi:{database.password}@127.0.0.1:{PORT}/movi_e2e\n',
            encoding='utf-8',
        )
    print('PostgreSQL local pronto em 127.0.0.1:55432; bancos movi_demo e movi_e2e separados.')
    print('Credenciais locais preservadas em .env e .env.e2e (ignorados pelo Git).')


if __name__ == '__main__':
    main()
