#!/bin/bash

set -e

# Stop PostgreSQL if it’s running
pg_ctl -D /home/postgres/.pgenv/pgsql/data stop || true


# Restart PostgreSQL to apply changes
pg_ctl -D /home/postgres/.pgenv/pgsql/data restart

# Set the password for the postgres user
echo "Setting password for postgres user..."
psql -U postgres -h localhost -c "ALTER USER postgres WITH PASSWORD 'Passwd34!';"

# Verify the password is set correctly
echo "Verifying password for postgres user..."
if PGPASSWORD='Passwd34!' psql -U postgres -h localhost -c 'SELECT 1' &>/dev/null; then
    echo "Password verified successfully. Restarting the PostgreSQL server..."
    pg_ctl -D /home/postgres/.pgenv/pgsql/data restart
else
    echo "Failed to verify password. Exiting."
    exit 1
fi

echo "listen_addresses = '*'" >> /home/postgres/.pgenv/pgsql/data/postgresql.conf

echo "host all all 0.0.0.0/0 md5" >> /home/postgres/.pgenv/pgsql/data/pg_hba.conf

pg_ctl -D /home/postgres/.pgenv/pgsql/data restart

# Keep the container running by tailing the log
tail -f /home/postgres/.pgenv/pgsql/data/server.log