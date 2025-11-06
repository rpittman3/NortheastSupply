#!/usr/bin/env python3
"""
Database Migration Tool for Professional Restaurant Supply
This tool helps you export and import your PostgreSQL database.

Usage:
    Export: python db_migrate.py export
    Import: python db_migrate.py import backup_file.sql
"""

import os
import sys
import subprocess
from datetime import datetime

def get_db_config():
    """Get database configuration from environment variables."""
    config = {
        'host': os.environ.get('PGHOST'),
        'port': os.environ.get('PGPORT'),
        'user': os.environ.get('PGUSER'),
        'password': os.environ.get('PGPASSWORD'),
        'database': os.environ.get('PGDATABASE'),
    }
    
    # Validate all required variables are present
    missing = [k for k, v in config.items() if not v]
    if missing:
        print(f"Error: Missing required environment variables: {', '.join(missing.upper())}")
        sys.exit(1)
    
    return config

def export_database():
    """Export the database to a SQL file using pg_dump."""
    print("Starting database export...")
    
    config = get_db_config()
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"database_backup_{timestamp}.sql"
    
    # Set PGPASSWORD environment variable for pg_dump
    env = os.environ.copy()
    env['PGPASSWORD'] = config['password']
    
    # Build pg_dump command
    cmd = [
        'pg_dump',
        '-h', config['host'],
        '-p', config['port'],
        '-U', config['user'],
        '-d', config['database'],
        '-F', 'p',  # Plain text format
        '-f', filename,
        '--no-owner',  # Don't include ownership commands
        '--no-privileges',  # Don't include privilege commands
    ]
    
    try:
        # Run pg_dump
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Check if file was created
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            print(f"\n✓ Export successful!")
            print(f"  File: {filename}")
            print(f"  Size: {size:,} bytes")
            print(f"\nTo use this backup in a new Repl:")
            print(f"  1. Download this file: {filename}")
            print(f"  2. Upload it to your new Repl")
            print(f"  3. Run: python db_migrate.py import {filename}")
        else:
            print("Error: Backup file was not created")
            sys.exit(1)
            
    except subprocess.CalledProcessError as e:
        print(f"Error during export: {e}")
        if e.stderr:
            print(f"Details: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

def import_database(filename):
    """Import a database from a SQL file using psql."""
    print(f"Starting database import from {filename}...")
    
    # Check if file exists
    if not os.path.exists(filename):
        print(f"Error: File '{filename}' not found")
        sys.exit(1)
    
    config = get_db_config()
    
    # Warn user about overwriting data
    print("\n⚠ WARNING: This will overwrite your current database!")
    response = input("Are you sure you want to continue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Import cancelled.")
        sys.exit(0)
    
    # Set PGPASSWORD environment variable for psql
    env = os.environ.copy()
    env['PGPASSWORD'] = config['password']
    
    # Build psql command
    cmd = [
        'psql',
        '-h', config['host'],
        '-p', config['port'],
        '-U', config['user'],
        '-d', config['database'],
        '-f', filename,
        '-q',  # Quiet mode
    ]
    
    try:
        # Run psql
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        
        print("\n✓ Import successful!")
        print("  Your database has been restored from the backup.")
        
    except subprocess.CalledProcessError as e:
        print(f"Error during import: {e}")
        if e.stderr:
            print(f"Details: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

def show_help():
    """Display help information."""
    print(__doc__)
    print("\nExamples:")
    print("  # Export current database")
    print("  python db_migrate.py export")
    print()
    print("  # Import from a backup file")
    print("  python db_migrate.py import database_backup_20251106_143022.sql")
    print()

def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'export':
        export_database()
    elif command == 'import':
        if len(sys.argv) < 3:
            print("Error: Please specify the backup file to import")
            print("Usage: python db_migrate.py import <filename.sql>")
            sys.exit(1)
        import_database(sys.argv[2])
    elif command in ['help', '-h', '--help']:
        show_help()
    else:
        print(f"Error: Unknown command '{command}'")
        show_help()
        sys.exit(1)

if __name__ == '__main__':
    main()
