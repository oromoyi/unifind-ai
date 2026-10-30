"""One-command database setup (creates the MySQL database, user, tables, reference data, optional demo data).

  python init_db.py --demo          # database + tables + demo accounts/items
  python init_db.py                 # database + tables + reference data only
  python init_db.py --reset --demo  # DROP all tables first, then rebuild

Needs a MySQL account allowed to CREATE DATABASE/USER (normally root). It asks for the root password,
or reads DB_ROOT_USER / DB_ROOT_PASSWORD from the environment / backend/.env.
If DB_USER in .env is 'root', that account is used directly and no extra user is created.
"""
import getpass
import os
import sys

import pymysql
from dotenv import load_dotenv

load_dotenv()


def main():
    host, port = os.getenv("DB_HOST", "127.0.0.1"), int(os.getenv("DB_PORT", "3306"))
    app_user, app_pw, name = os.getenv("DB_USER", "unifind"), os.getenv("DB_PASSWORD", ""), os.getenv("DB_NAME", "unifind")
    if not os.getenv("DATABASE_URL"):
        root_user = os.getenv("DB_ROOT_USER", "root")
        if app_user == "root":
            root_pw = app_pw
        else:
            root_pw = os.getenv("DB_ROOT_PASSWORD")
            if root_pw is None:
                root_pw = getpass.getpass(f"MySQL password for '{root_user}' (press Enter if none): ")
        try:
            conn = pymysql.connect(host=host, port=port, user=root_user, password=root_pw, autocommit=True)
        except pymysql.err.OperationalError as e:
            sys.exit(f"\nCannot connect to MySQL at {host}:{port} as '{root_user}': {e}\n"
                     "-> Is MySQL running? (PowerShell: Get-Service *mysql*  /  Start-Service MySQL80)\n"
                     "-> Is the root password correct?")
        with conn.cursor() as c:
            c.execute(f"CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            if app_user != "root":
                for h in ("localhost", "127.0.0.1", "%"):
                    c.execute(f"CREATE USER IF NOT EXISTS %s@%s IDENTIFIED BY %s", (app_user, h, app_pw))
                    c.execute(f"ALTER USER %s@%s IDENTIFIED BY %s", (app_user, h, app_pw))
                    c.execute(f"GRANT ALL PRIVILEGES ON `{name}`.* TO %s@%s", (app_user, h))
                c.execute("FLUSH PRIVILEGES")
        conn.close()
        print(f"Database '{name}' and user '{app_user}' are ready.")
    # tables + reference data (+ demo data) via seed.py
    import seed
    sys.argv = [sys.argv[0]] + [a for a in sys.argv[1:] if a in ("--reset", "--demo")]
    if "--demo" not in sys.argv:
        sys.argv.append("--bootstrap-only")
    else:
        sys.argv.remove("--demo")
    seed.main()
    print("\nDone. Now start the API:  python run.py")


if __name__ == "__main__":
    main()
