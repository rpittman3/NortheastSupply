# Database Migration Guide

This guide explains how to copy your Professional Restaurant Supply database from one Repl to another.

## Overview

The `db_migrate.py` tool helps you create a complete backup of your database and restore it in a new Repl. This is useful when you want to duplicate your application with all its data.

## How to Copy Your App to a New Repl

### Step 1: Export the Database (In Your Original Repl)

Run the export command:

```bash
python db_migrate.py export
```

This creates a backup file named `database_backup_YYYYMMDD_HHMMSS.dump` with:
- All table structures (categories, products, orders, users, etc.)
- All data (your actual products, orders, customer information, etc.)
- All relationships and constraints

**Example output:**
```
✓ Export successful!
  File: database_backup_20251109_010940.dump
  Size: 258,053 bytes
```

### Step 2: Download the Backup File

1. Find the backup file in your file explorer (left sidebar)
2. Right-click on `database_backup_YYYYMMDD_HHMMSS.dump`
3. Select "Download" to save it to your computer

### Step 3: Create Your New Repl

1. Fork this Repl or create a new copy
2. The new Repl will automatically get its own empty PostgreSQL database
3. All your code will be copied, but the database will be empty

### Step 4: Upload the Backup File (In Your New Repl)

1. In your new Repl, click the "Upload file" button
2. Select the `database_backup_YYYYMMDD_HHMMSS.dump` file you downloaded
3. Upload it to the root directory

### Step 5: Import the Database (In Your New Repl)

Run the import command:

```bash
python db_migrate.py import database_backup_20251109_010940.dump
```

**Important:** Replace `database_backup_20251109_010940.dump` with your actual filename.

You'll see a warning:
```
⚠ WARNING: This will overwrite your current database!
Are you sure you want to continue? (yes/no):
```

Type `yes` and press Enter.

**Example output:**
```
✓ Import successful!
  Your database has been restored from the backup.
```

### Step 6: Verify the Import

1. Restart your application workflow
2. Visit your website and check that:
   - All products are visible
   - All categories are present
   - Orders are showing (if you're an admin)
   - Everything works as expected

## What Gets Copied

✅ **Included in the backup:**
- All products with prices, descriptions, and specifications
- All categories and their hierarchy
- All manufacturers
- All orders and order history
- All user accounts
- All shopping cart data
- All quote requests
- Database relationships and constraints

❌ **NOT included in the backup:**
- Uploaded images (static files)
- Environment variables (SMTP settings, secrets, etc.)
- Code files (these are copied when you fork)

## Troubleshooting

### "File not found" error
Make sure you've uploaded the backup file to the root directory of your new Repl.

### "Permission denied" error
This usually means the database connection isn't configured. Verify that your new Repl has a PostgreSQL database provisioned.

### Import seems stuck
The import can take 30-60 seconds for large databases. Be patient and let it complete.

### Tables already exist error
If you need to do a fresh import, you can manually drop all tables first using the database tools, then run the import again.

## Command Reference

### Export Database
```bash
python db_migrate.py export
```
Creates a new backup file with timestamp.

### Import Database
```bash
python db_migrate.py import <filename.dump>
```
Restores database from the specified backup file.

**Note:** The tool automatically detects the file format. It supports both:
- `.dump` files (new custom format - recommended)
- `.sql` files (old plain text format - for backward compatibility)

### Help
```bash
python db_migrate.py help
```
Shows usage information.

## Tips

1. **Regular Backups:** Consider exporting your database regularly as a backup, even if you're not copying to a new Repl
2. **Filename:** Keep the timestamp in the filename so you know when the backup was created
3. **File Size:** The new custom format creates smaller, compressed backups (about 5x smaller than old SQL format)
4. **Special Characters:** The custom format properly handles products with quotes, newlines, and HTML in descriptions
5. **Testing:** After importing, test all major features to ensure everything works correctly
6. **Environment Variables:** Remember to set up your SMTP settings and other environment variables in the new Repl

## Need Help?

If you encounter issues:
1. Check that both Repls have PostgreSQL databases provisioned
2. Verify the backup file was uploaded correctly
3. Make sure you're using the exact filename in the import command
4. Check the Repl console for any error messages
