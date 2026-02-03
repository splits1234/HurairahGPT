# HurairahGPT Migration System Documentation

## Overview

The HurairahGPT migration system automatically migrates data from file-based storage (`.txt` and `.json` files) to an embedded SQLite database. This provides:
- **Zero-setup deployment**: Works immediately after `git clone`
- **Auto-migration**: Automatically detects and imports data on startup
- **Data integrity**: Maintains relationships and handles type conversions
- **Change detection**: Only migrates changed files (efficient re-runs)
- **Error handling**: Graceful handling of malformed files

## Architecture

```
HurairahGPT/
├── mysite/
│   ├── database.py      # SQLite database module
│   ├── parser.py        # File parsing module
│   ├── migration.py     # Auto-migration system
│   ├── flask_app.py     # Flask application (updated)
│   ├── credentials.txt  # Source: email:password pairs
│   ├── users.json       # Source: user data with sessions
│   ├── rate_limits.json # Source: rate limiting data
│   └── hurairahgpt.db   # Target: SQLite database (auto-created)
```

## Supported Data Sources

### 1. credentials.txt

**Format**: Key-value pairs with delimiters (`:`, `=`, `,`, ` `, `\t`)

**Example**:
```text
# Comments are ignored
user@example.com:password123
admin@test.com=secretpass
guest@test.com, guestpassword
```

**Migrated to**: `users` table (email, password_hash fields)

### 2. users.json

**Format**: Nested JSON with user data and sessions

**Example**:
```json
{
  "user@example.com": {
    "sessions": {
      "uuid-1": {
        "name": "Chat 1",
        "history": [
          {"content": "Hello", "sender": "user", "time": "2026-01-01 12:00:00"},
          {"content": "Hi!", "sender": "bot", "time": "2026-01-01 12:00:01"}
        ],
        "created": "2026-01-01 12:00:00"
      }
    },
    "active_session": "uuid-1",
    "theme": "dark",
    "personality": "default",
    "tier": "free",
    "image_usage": {
      "last_reset": "2026-01-01T12:00:00",
      "count": 0
    },
    "upgrade_history": []
  }
}
```

**Migrated to**: `users`, `sessions`, and `messages` tables

### 3. rate_limits.json

**Format**: JSON object with rate limit data

**Example**:
```json
{
  "192.168.1.1": {
    "request_count": 10,
    "window_start": "2026-01-01T12:00:00"
  }
}
```

**Migrated to**: `rate_limits` table

## Database Schema

### users table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| email | TEXT | Unique user email |
| password_hash | TEXT | Password hash (nullable) |
| theme | TEXT | UI theme preference |
| personality | TEXT | AI personality |
| tier | TEXT | User tier (free/premium/unlimited) |
| image_usage_count | INTEGER | Image generation count |
| image_usage_last_reset | TEXT | Last reset timestamp |
| upgrade_history | TEXT | JSON array of upgrades |
| created_at | TEXT | Creation timestamp |
| updated_at | TEXT | Last update timestamp |

### sessions table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| user_id | INTEGER | Foreign key to users |
| session_id | TEXT | Unique session UUID |
| name | TEXT | Session name |
| created_at | TEXT | Creation timestamp |
| updated_at | TEXT | Last update timestamp |

### messages table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| session_id | TEXT | Foreign key to sessions |
| content | TEXT | Message content |
| sender | TEXT | 'user' or 'bot' |
| time | TEXT | Message timestamp |
| metadata | TEXT | JSON for additional data |
| created_at | TEXT | Creation timestamp |

### rate_limits table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| identifier | TEXT | IP or user identifier |
| limit_type | TEXT | 'ip' or 'user' |
| request_count | INTEGER | Requests in window |
| window_start | TEXT | Window start timestamp |
| created_at | TEXT | Creation timestamp |
| updated_at | TEXT | Last update timestamp |

### migration_log table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| migration_name | TEXT | Migration name |
| migration_version | INTEGER | Schema version |
| started_at | TEXT | Start timestamp |
| completed_at | TEXT | Completion timestamp |
| status | TEXT | pending/running/completed/failed |
| records_migrated | INTEGER | Records migrated |
| errors | TEXT | JSON array of errors |

## Usage

### Automatic Migration

The migration runs automatically when the Flask application starts:

```bash
python flask_app.py
```

Output:
```
2026-02-02 11:00:00 - INFO - Database initialized successfully
2026-02-02 11:00:00 - INFO - Starting automatic data migration...
2026-02-02 11:00:00 - INFO - Migrating credentials from /path/to/credentials.txt
2026-02-02 11:00:00 - INFO - Migrated user: user@example.com
2026-02-02 11:00:00 - INFO - Credentials migration complete: 1 users
2026-02-02 11:00:00 - INFO - Migrating users from /path/to/users.json
2026-02-02 11:00:00 - INFO - Migrated user: user@example.com
2026-02-02 11:00:00 - INFO - Users migration complete: 2 users/sessions
2026-02-02 11:00:00 - INFO - ================================
2026-02-02 11:00:00 - INFO - Migration Complete
2026-02-02 11:00:00 - INFO -   Files scanned: 3
2026-02-02 11:00:00 - INFO -   Files migrated: 2
2026-02-02 11:00:00 - INFO -   Records migrated: 5
2026-02-02 11:00:00 - INFO -   Errors: 0
2026-02-02 11:00:00 - INFO -   Warnings: 1
2026-02-02 11:00:00 - INFO -   Duration: 0.05s
2026-02-02 11:00:00 - INFO - Database stats: 2 users, 3 sessions, 10 messages
```

### Manual Migration via API

Trigger migration via HTTP request:

```bash
# Normal migration (only changed files)
curl -X POST http://localhost:5000/api/migration/run

# Force migration (all files)
curl -X POST "http://localhost:5000/api/migration/run?force=true"
```

Response:
```json
{
  "success": true,
  "message": "Migration completed with 0 errors",
  "results": {
    "files_scanned": 3,
    "files_migrated": 1,
    "records_migrated": 5,
    "errors": 0,
    "warnings": 1,
    "duration_seconds": 0.05
  }
}
```

### Check Migration Status

```bash
curl http://localhost:5000/api/migration/status
```

Response:
```json
{
  "success": true,
  "migration_status": {
    "database_exists": true,
    "database_stats": {
      "user_count": 2,
      "session_count": 3,
      "message_count": 10
    },
    "last_migration": "2026-02-02T11:00:00.000000",
    "files_monitored": ["credentials.txt", "users.json", "rate_limits.json"]
  },
  "database_stats": {
    "user_count": 2,
    "session_count": 3,
    "message_count": 10
  }
}
```

### Database Statistics

```bash
curl http://localhost:5000/api/migration/stats
```

Response:
```json
{
  "success": true,
  "stats": {
    "user_count": 2,
    "session_count": 3,
    "message_count": 10
  }
}
```

### Command Line Migration

Run migration from command line:

```bash
# Run migration from mysite directory
cd HurairahGPT/main/mysite
python migration.py

# Force migration (re-migrate all files)
python migration.py --force

# Migrate specific file
python migration.py --file users.json --type users

# Check status only
python migration.py --status
```

## Adding New Data Sources

### Step 1: Create a Parser

Add a new parser class in [`parser.py`](parser.py):

```python
class NewDataParser:
    @staticmethod
    def parse(file_path: str) -> Dict[str, Any]:
        """Parse the data file."""
        # Your parsing logic here
        pass
```

### Step 2: Add Migration Method

Add a migration method in [`migration.py`](migration.py):

```python
def _migrate_new_data(self, file_path: str, 
                      errors: List[str], 
                      warnings: List[str]) -> int:
    """Migrate new data source."""
    data = NewDataParser.parse(file_path)
    migrated = 0
    
    for item in data:
        try:
            # Your migration logic here
            migrated += 1
        except Exception as e:
            errors.append(f"Failed to migrate item: {e}")
    
    return migrated
```

### Step 3: Update DEFAULT_DATA_FILES

Update the mapping in [`migration.py`](migration.py):

```python
DEFAULT_DATA_FILES = {
    'credentials': 'credentials.txt',
    'users': 'users.json',
    'rate_limits': 'rate_limits.json',
    'new_data': 'new_data.json'  # Add this
}
```

### Step 4: Update run_auto_migration

Add handling for the new data type:

```python
if migration_name == 'new_data':
    records_migrated = self._migrate_new_data(file_path, errors, warnings)
```

## Error Handling

### Malformed Files

The system handles malformed files gracefully:

- **JSON parse errors**: Logged as warnings, migration continues
- **Missing fields**: Uses default values, logs warnings
- **Duplicate entries**: Skipped with warning, existing data preserved
- **Invalid data types**: Converted with fallback values

### Logging

All migration operations are logged to:
1. Console (stdout)
2. `migration.log` file

Example log levels:
- `INFO`: Migration steps and progress
- `WARNING`: Non-critical issues (missing fields, duplicates)
- `ERROR`: Critical failures (parse errors, database errors)

## Change Detection

The system uses file hash comparison to detect changes:

1. First migration: Hash all files, migrate all data
2. Subsequent migrations: Re-hash files, only migrate changed files
3. Force flag: Skip change detection, migrate all files

This prevents unnecessary re-migration of unchanged data.

## Rollback and Recovery

### Backup Before Migration

```bash
# Backup data files
cp credentials.txt credentials.txt.backup
cp users.json users.json.backup
cp rate_limits.json rate_limits.json.backup
```

### Restore from Backup

```bash
# Restore data files
cp credentials.txt.backup credentials.txt
cp users.json.backup users.json
cp rate_limits.json.backup rate_limits.json

# Delete database (will be recreated on next start)
rm hurairahgpt.db
```

### Manual Database Access

```bash
# View database contents
sqlite3 hurairahgpt.db

# SQLite commands:
# .tables          # List all tables
# .schema users    # Show users table schema
# SELECT * FROM users;  # View all users
# .exit            # Exit
```

## Performance Considerations

- **Initial migration**: Depends on data size (typically < 1 second for small datasets)
- **Subsequent migrations**: Only changed files are processed
- **Database size**: SQLite scales well for single-user applications (up to ~140TB)
- **Concurrent access**: SQLite supports multiple readers, single writer

## Troubleshooting

### Migration Fails to Run

1. Check Python dependencies:
   ```bash
   pip install flask openai pillow
   ```

2. Check file permissions:
   ```bash
   chmod 644 credentials.txt users.json rate_limits.json
   ```

3. Check log file:
   ```bash
   cat migration.log
   ```

### Data Not Migrating

1. Verify file format matches expected structure
2. Check for parsing errors in logs
3. Run with `--force` flag to re-migrate all data
4. Check database exists: `ls -la hurairahgpt.db`

### Database Connection Errors

1. Check disk space
2. Verify file permissions on database directory
3. Check for file locks

## File Formats Reference

### TXT Format

Supported delimiters (in order of priority):
1. `:` - Key:Value format
2. `=` - Key=Value format
3. `,` - CSV format
4. `\t` - TSV format
5. ` ` - Space-separated

Comments: Lines starting with `#` or `//` are ignored.

### JSON Format

Must be valid JSON. Supported structures:
- Object: `{"key": "value"}`
- Array: `[{"id": 1}, {"id": 2}]`
- Nested objects: `{"user": {"name": "John"}}`

## API Reference

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/migration/status` | Get migration and database status |
| POST | `/api/migration/run` | Trigger manual migration |
| GET | `/api/migration/stats` | Get database statistics |

### Response Format

Success response:
```json
{
  "success": true,
  "message": "Operation completed",
  "results": { ... }
}
```

Error response:
```json
{
  "success": false,
  "error": "Error description"
}
```

## License

This migration system is part of HurairahGPT. See main LICENSE file for details.
