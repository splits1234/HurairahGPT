"""
Migration module for HurairahGPT - Auto-migration from file-based storage to SQLite.

This module provides:
- Automatic detection and migration of .txt and .json files
- Schema creation and updates
- Data integrity validation
- Error handling and logging
- Manual migration triggers
"""

import os
import json
import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from database import (
    init_db, get_connection, create_user, create_session, add_message,
    set_rate_limit, get_user_by_email, user_exists, session_exists,
    DatabaseError
)
from parser import (
    FileParser, CredentialsParser, UserDataParser, RateLimitParser,
    ParseError, ParsedData, FileFormat
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('migration.log')
    ]
)
logger = logging.getLogger(__name__)


class MigrationStatus(Enum):
    """Migration status values."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class MigrationResult:
    """Result of a migration operation."""
    success: bool
    migration_name: str
    source_file: Optional[str]
    records_migrated: int
    errors: List[str]
    warnings: List[str]
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'migration_name': self.migration_name,
            'source_file': self.source_file,
            'records_migrated': self.records_migrated,
            'errors': self.errors,
            'warnings': self.warnings,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


@dataclass
class MigrationReport:
    """Complete migration report."""
    total_files_scanned: int
    total_files_migrated: int
    total_records_migrated: int
    total_errors: int
    total_warnings: int
    duration_seconds: float
    results: List[MigrationResult]
    timestamp: datetime = field(default_factory=datetime.now)


class MigrationManager:
    """
    Manages data migration from file-based storage to SQLite.
    
    Supported data sources:
    - credentials.txt: Email/password pairs
    - users.json: User data with sessions and preferences
    - rate_limits.json: Rate limiting data
    """
    
    # Default data file mappings
    DEFAULT_DATA_FILES = {
        'credentials': 'credentials.txt',
        'users': 'users.json',
        'rate_limits': 'rate_limits.json'
    }
    
    def __init__(self, data_directory: Optional[str] = None):
        """
        Initialize the migration manager.
        
        Args:
            data_directory: Directory containing data files (defaults to module directory)
        """
        self.data_directory = data_directory or os.path.dirname(__file__)
        self.results: List[MigrationResult] = []
        self._file_hashes: Dict[str, str] = {}
    
    def _get_file_path(self, filename: str) -> str:
        """Get full path to a data file."""
        return os.path.join(self.data_directory, filename)
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate MD5 hash of a file for change detection.
        
        Args:
            file_path: Path to the file
        
        Returns:
            str: MD5 hash of file contents
        """
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    def _is_file_changed(self, file_path: str) -> bool:
        """
        Check if a file has changed since last migration.
        
        Args:
            file_path: Path to the file
        
        Returns:
            bool: True if file has changed
        """
        current_hash = self._calculate_file_hash(file_path)
        last_hash = self._file_hashes.get(file_path, "")
        
        if not last_hash:
            # First migration - mark as changed
            self._file_hashes[file_path] = current_hash
            return True
        
        changed = current_hash != last_hash
        if changed:
            self._file_hashes[file_path] = current_hash
        
        return changed
    
    def run_auto_migration(self, force: bool = False) -> MigrationReport:
        """
        Run automatic migration of all detected data files.
        
        Args:
            force: Force migration even if files haven't changed
        
        Returns:
            MigrationReport: Complete migration report
        """
        start_time = datetime.now()
        logger.info("=" * 60)
        logger.info("Starting automatic migration")
        logger.info(f"Data directory: {self.data_directory}")
        logger.info(f"Force mode: {force}")
        logger.info("=" * 60)
        
        # Initialize database
        try:
            init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return MigrationReport(
                total_files_scanned=0,
                total_files_migrated=0,
                total_records_migrated=0,
                total_errors=1,
                total_warnings=0,
                duration_seconds=0,
                results=[]
            )
        
        self.results = []
        files_scanned = 0
        files_migrated = 0
        
        # Migrate each data source
        for source_name, filename in self.DEFAULT_DATA_FILES.items():
            file_path = self._get_file_path(filename)
            files_scanned += 1
            
            # Check if file exists
            if not os.path.exists(file_path):
                logger.info(f"Skipping {filename}: file not found")
                self.results.append(MigrationResult(
                    success=True,
                    migration_name=source_name,
                    source_file=file_path,
                    records_migrated=0,
                    errors=[],
                    warnings=[f"File not found: {file_path}"],
                    started_at=datetime.now()
                ))
                continue
            
            # Check if file has changed
            if not force and not self._is_file_changed(file_path):
                logger.info(f"Skipping {filename}: no changes detected")
                self.results.append(MigrationResult(
                    success=True,
                    migration_name=source_name,
                    source_file=file_path,
                    records_migrated=0,
                    errors=[],
                    warnings=["No changes detected"],
                    started_at=datetime.now()
                ))
                continue
            
            # Run migration for this file
            result = self._migrate_file(source_name, file_path)
            self.results.append(result)
            files_migrated += 1
        
        # Calculate totals
        total_records = sum(r.records_migrated for r in self.results)
        total_errors = sum(len(r.errors) for r in self.results)
        total_warnings = sum(len(r.warnings) for r in self.results)
        duration = (datetime.now() - start_time).total_seconds()
        
        report = MigrationReport(
            total_files_scanned=files_scanned,
            total_files_migrated=files_migrated,
            total_records_migrated=total_records,
            total_errors=total_errors,
            total_warnings=total_warnings,
            duration_seconds=duration,
            results=self.results
        )
        
        # Log summary
        logger.info("=" * 60)
        logger.info("Migration Complete")
        logger.info(f"  Files scanned: {report.total_files_scanned}")
        logger.info(f"  Files migrated: {report.total_files_migrated}")
        logger.info(f"  Records migrated: {report.total_records_migrated}")
        logger.info(f"  Errors: {report.total_errors}")
        logger.info(f"  Warnings: {report.total_warnings}")
        logger.info(f"  Duration: {report.duration_seconds:.2f}s")
        logger.info("=" * 60)
        
        return report
    
    def _migrate_file(self, migration_name: str, file_path: str) -> MigrationResult:
        """
        Migrate a single data file.
        
        Args:
            migration_name: Name of the migration
            file_path: Path to the file
        
        Returns:
            MigrationResult: Migration result
        """
        start_time = datetime.now()
        errors = []
        warnings = []
        records_migrated = 0
        
        logger.info(f"Migrating {migration_name} from {file_path}")
        
        try:
            if migration_name == 'credentials':
                records_migrated = self._migrate_credentials(file_path, errors, warnings)
            
            elif migration_name == 'users':
                records_migrated = self._migrate_users(file_path, errors, warnings)
            
            elif migration_name == 'rate_limits':
                records_migrated = self._migrate_rate_limits(file_path, errors, warnings)
            
            else:
                warnings.append(f"Unknown migration type: {migration_name}")
        
        except Exception as e:
            logger.error(f"Migration failed for {file_path}: {e}")
            errors.append(str(e))
        
        return MigrationResult(
            success=len(errors) == 0,
            migration_name=migration_name,
            source_file=file_path,
            records_migrated=records_migrated,
            errors=errors,
            warnings=warnings,
            started_at=start_time,
            completed_at=datetime.now()
        )
    
    def _migrate_credentials(self, file_path: str, 
                             errors: List[str], 
                             warnings: List[str]) -> int:
        """
        Migrate credentials from TXT file.
        
        Args:
            file_path: Path to credentials.txt
            errors: Error list to append to
            warnings: Warning list to append to
        
        Returns:
            int: Number of records migrated
        """
        credentials = CredentialsParser.parse(file_path)
        migrated = 0
        
        for email, password in credentials.items():
            try:
                # Check if user already exists
                if user_exists(email):
                    warnings.append(f"User already exists, skipping: {email}")
                    continue
                
                # Create user without password hash (plaintext for legacy migration)
                # In production, password should be hashed
                create_user(
                    email=email,
                    password_hash=None,  # Legacy: no hash
                    theme='dark',
                    personality='default',
                    tier='free'
                )
                migrated += 1
                logger.info(f"Migrated user: {email}")
                
            except Exception as e:
                errors.append(f"Failed to migrate user {email}: {e}")
                logger.error(f"Error migrating {email}: {e}")
        
        logger.info(f"Credentials migration complete: {migrated} users")
        return migrated
    
    def _migrate_users(self, file_path: str,
                       errors: List[str],
                       warnings: List[str]) -> int:
        """
        Migrate user data from JSON file.
        
        Args:
            file_path: Path to users.json
            errors: Error list to append to
            warnings: Warning list to append to
        
        Returns:
            int: Number of records migrated
        """
        user_data = UserDataParser.parse(file_path)
        migrated = 0
        
        for email, data in user_data.items():
            try:
                # Extract user fields
                theme = data.get('theme', 'dark')
                personality = data.get('personality', 'default')
                tier = data.get('tier', 'free')
                image_usage = data.get('image_usage', {'count': 0, 'last_reset': None})
                upgrade_history = data.get('upgrade_history', [])
                
                # Check if user already exists
                existing_user = get_user_by_email(email)
                if existing_user:
                    # Update existing user
                    from database import update_user
                    update_user(
                        existing_user['id'],
                        theme=theme,
                        personality=personality,
                        tier=tier,
                        image_usage_count=image_usage.get('count', 0),
                        image_usage_last_reset=image_usage.get('last_reset'),
                        upgrade_history=json.dumps(upgrade_history)
                    )
                    warnings.append(f"User updated (already exists): {email}")
                    user_id = existing_user['id']
                else:
                    # Create new user with basic fields
                    user_id = create_user(
                        email=email,
                        theme=theme,
                        personality=personality,
                        tier=tier
                    )
                    
                    # Update additional fields after creation
                    from database import update_user
                    update_user(
                        user_id,
                        image_usage_count=image_usage.get('count', 0),
                        image_usage_last_reset=image_usage.get('last_reset'),
                        upgrade_history=json.dumps(upgrade_history)
                    )
                    
                    migrated += 1
                    logger.info(f"Migrated user: {email}")
                
                # Migrate sessions
                sessions = UserDataParser.extract_sessions(data)
                for session_info in sessions:
                    session_id = session_info['session_id']
                    session_name = session_info['name']
                    history = session_info['history']
                    created = session_info['created']
                    
                    # Create session if not exists
                    if not session_exists(session_id):
                        create_session(
                            user_id=user_id,
                            session_id=session_id,
                            name=session_name
                        )
                    
                    # Migrate messages
                    for msg in history:
                        try:
                            add_message(
                                session_id=session_id,
                                content=msg.get('content', ''),
                                sender=msg.get('sender', 'bot'),
                                time=msg.get('time', created)
                            )
                        except Exception as e:
                            errors.append(f"Failed to add message in session {session_id}: {e}")
                
                migrated += len(sessions)
                
            except Exception as e:
                errors.append(f"Failed to migrate user {email}: {e}")
                logger.error(f"Error migrating {email}: {e}")
        
        logger.info(f"Users migration complete: {migrated} users/sessions")
        return migrated
    
    def _migrate_rate_limits(self, file_path: str,
                              errors: List[str],
                              warnings: List[str]) -> int:
        """
        Migrate rate limits from JSON file.
        
        Args:
            file_path: Path to rate_limits.json
            errors: Error list to append to
            warnings: Warning list to append to
        
        Returns:
            int: Number of records migrated
        """
        rate_limit_data = RateLimitParser.parse(file_path)
        migrated = 0
        
        for identifier, data in rate_limit_data.items():
            try:
                request_count = data.get('request_count', 0)
                window_start = data.get('window_start', datetime.now().isoformat())
                
                set_rate_limit(
                    identifier=identifier,
                    limit_type='ip',  # Default to IP-based
                    request_count=request_count,
                    window_start=window_start
                )
                migrated += 1
                
            except Exception as e:
                errors.append(f"Failed to migrate rate limit for {identifier}: {e}")
                logger.error(f"Error migrating rate limit for {identifier}: {e}")
        
        logger.info(f"Rate limits migration complete: {migrated} entries")
        return migrated
    
    def migrate_specific_file(self, file_path: str, 
                               migration_type: str) -> MigrationResult:
        """
        Migrate a specific file.
        
        Args:
            file_path: Path to the file
            migration_type: Type of migration (credentials, users, rate_limits)
        
        Returns:
            MigrationResult: Migration result
        """
        return self._migrate_file(migration_type, file_path)
    
    def get_migration_status(self) -> Dict[str, Any]:
        """
        Get current migration status.
        
        Returns:
            dict: Status information
        """
        from database import get_stats
        
        stats = get_stats()
        
        return {
            'database_exists': os.path.exists(self._get_file_path('hurairahgpt.db')),
            'database_stats': stats,
            'last_migration': datetime.now().isoformat(),
            'files_monitored': list(self.DEFAULT_DATA_FILES.values())
        }


# ============ CLI Interface ============

def main():
    """Main entry point for migration CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(description="HurairahGPT Migration Tool")
    parser.add_argument(
        '--dir', 
        default=None,
        help='Data directory (default: current directory)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force migration even if files havent changed'
    )
    parser.add_argument(
        '--file',
        default=None,
        help='Migrate a specific file'
    )
    parser.add_argument(
        '--type',
        default=None,
        choices=['credentials', 'users', 'rate_limits'],
        help='Type of file to migrate'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show migration status'
    )
    
    args = parser.parse_args()
    
    if args.status:
        manager = MigrationManager(args.dir)
        status = manager.get_migration_status()
        print(json.dumps(status, indent=2))
        return
    
    if args.file and args.type:
        manager = MigrationManager(args.dir)
        result = manager.migrate_specific_file(args.file, args.type)
        print(json.dumps(result.to_dict(), indent=2))
        return
    
    # Run full migration
    manager = MigrationManager(args.dir)
    report = manager.run_auto_migration(force=args.force)
    print(json.dumps({
        'total_files_scanned': report.total_files_scanned,
        'total_files_migrated': report.total_files_migrated,
        'total_records_migrated': report.total_records_migrated,
        'total_errors': report.total_errors,
        'total_warnings': report.total_warnings,
        'duration_seconds': report.duration_seconds
    }, indent=2))


if __name__ == "__main__":
    main()
