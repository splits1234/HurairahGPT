"""
File parser module for HurairahGPT - Parses .txt and .json data files.

This module provides:
- TXT file parsing (key-value pairs, delimited formats)
- JSON file parsing (structured data extraction)
- Format detection and validation
- Error handling for malformed files
"""

import json
import os
import re
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FileFormat(Enum):
    """Supported file formats."""
    JSON = "json"
    TXT_KEY_VALUE = "txt_key_value"
    TXT_CSV = "txt_csv"
    TXT_TSV = "txt_tsv"
    TXT_DELIMITED = "txt_delimited"
    UNKNOWN = "unknown"


class ParseError(Exception):
    """Custom exception for parsing errors."""
    def __init__(self, message: str, file_path: str, line_number: Optional[int] = None):
        self.message = message
        self.file_path = file_path
        self.line_number = line_number
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        if self.line_number:
            return f"Parse error in {self.file_path} (line {self.line_number}): {self.message}"
        return f"Parse error in {self.file_path}: {self.message}"


@dataclass
class ParsedData:
    """Container for parsed file data."""
    format: FileFormat
    data: Union[Dict[str, Any], List[Dict[str, Any]], List[Any]]
    source_file: str
    item_count: int
    errors: List[str]


class FileParser:
    """
    Parser for various data file formats.
    
    Supports:
    - JSON files (.json)
    - Key-value TXT files (.txt) - format: key:value or key=value
    - CSV-like TXT files (.csv) - comma-delimited
    - TSV-like TXT files (.tsv) - tab-delimited
    - Custom delimited TXT files
    """
    
    # Default delimiters for TXT parsing
    DEFAULT_DELIMITERS = [':', '=', ',']
    
    def __init__(self, delimiters: Optional[List[str]] = None):
        """
        Initialize the parser.
        
        Args:
            delimiters: List of delimiters to try for TXT files (in order of priority)
        """
        self.delimiters = delimiters or self.DEFAULT_DELIMITERS
    
    def detect_format(self, file_path: str) -> FileFormat:
        """
        Detect the format of a file based on extension and content.
        
        Args:
            file_path: Path to the file
        
        Returns:
            FileFormat: Detected file format
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.json':
            return FileFormat.JSON
        
        if ext in ['.txt', '.csv', '.tsv']:
            # Check if it looks like key-value pairs
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    first_lines = [f.readline().strip() for _ in range(min(5, 100))]
                
                # Count delimiters in first few lines
                delimiter_counts = {}
                for line in first_lines:
                    if not line:
                        continue
                    for delim in self.delimiters:
                        count = line.count(delim)
                        if count > 0:
                            delimiter_counts[delim] = delimiter_counts.get(delim, 0) + count
                
                if delimiter_counts:
                    # Most common delimiter wins
                    most_common = max(delimiter_counts, key=delimiter_counts.get)
                    
                    if most_common == ',':
                        return FileFormat.TXT_CSV
                    elif most_common == '\t':
                        return FileFormat.TXT_TSV
                    else:
                        return FileFormat.TXT_DELIMITED
                
                return FileFormat.TXT_KEY_VALUE
                
            except Exception as e:
                logger.warning(f"Could not detect format for {file_path}: {e}")
                return FileFormat.UNKNOWN
        
        return FileFormat.UNKNOWN
    
    def parse_file(self, file_path: str) -> ParsedData:
        """
        Parse a data file and return structured data.
        
        Args:
            file_path: Path to the file to parse
        
        Returns:
            ParsedData: Parsed data container
        
        Raises:
            FileNotFoundError: If file doesn't exist
            ParseError: If file cannot be parsed
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        format_type = self.detect_format(file_path)
        errors = []
        
        try:
            if format_type == FileFormat.JSON:
                return self._parse_json(file_path)
            elif format_type in [FileFormat.TXT_KEY_VALUE, FileFormat.TXT_DELIMITED]:
                return self._parse_txt_key_value(file_path)
            elif format_type == FileFormat.TXT_CSV:
                return self._parse_txt_delimited(file_path, delimiter=',')
            elif format_type == FileFormat.TXT_TSV:
                return self._parse_txt_delimited(file_path, delimiter='\t')
            else:
                # Try JSON first, then TXT
                try:
                    return self._parse_json(file_path)
                except (json.JSONDecodeError, Exception):
                    return self._parse_txt_key_value(file_path)
                    
        except ParseError:
            raise
        except Exception as e:
            raise ParseError(str(e), file_path)
    
    def _parse_json(self, file_path: str) -> ParsedData:
        """
        Parse a JSON file.
        
        Args:
            file_path: Path to the JSON file
        
        Returns:
            ParsedData: Parsed JSON data
        
        Raises:
            ParseError: If JSON is malformed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Handle empty files
            if not content.strip():
                return ParsedData(
                    format=FileFormat.JSON,
                    data={},
                    source_file=file_path,
                    item_count=0,
                    errors=["Empty JSON file"]
                )
            
            # Try to parse as JSON
            data = json.loads(content)
            
            # Normalize data type
            if isinstance(data, dict):
                item_count = len(data)
            elif isinstance(data, list):
                item_count = len(data)
            else:
                data = {"value": data}
                item_count = 1
            
            logger.info(f"Parsed JSON file: {file_path} ({item_count} items)")
            
            return ParsedData(
                format=FileFormat.JSON,
                data=data,
                source_file=file_path,
                item_count=item_count,
                errors=[]
            )
            
        except json.JSONDecodeError as e:
            raise ParseError(f"Invalid JSON: {e}", file_path, e.lineno)
    
    def _parse_txt_key_value(self, file_path: str) -> ParsedData:
        """
        Parse a TXT file with key-value pairs.
        
        Format: key:value or key=value
        Lines starting with # or // are treated as comments.
        
        Args:
            file_path: Path to the TXT file
        
        Returns:
            ParsedData: Parsed key-value data
        """
        result_data = {}
        errors = []
        line_number = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_number, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#') or line.startswith('//'):
                        continue
                    
                    # Try to find delimiter
                    parsed = False
                    for delim in self.delimiters:
                        if delim in line:
                            parts = line.split(delim, 1)
                            if len(parts) == 2:
                                key = parts[0].strip()
                                value = parts[1].strip()
                                
                                # Don't overwrite existing keys (first occurrence wins)
                                if key not in result_data:
                                    result_data[key] = value
                                    parsed = True
                                else:
                                    errors.append(f"Line {line_number}: Duplicate key '{key}', skipping")
                                break
                    
                    if not parsed and line:
                        errors.append(f"Line {line_number}: Could not parse line: '{line}'")
            
            item_count = len(result_data)
            logger.info(f"Parsed TXT key-value file: {file_path} ({item_count} items)")
            
            return ParsedData(
                format=FileFormat.TXT_KEY_VALUE,
                data=result_data,
                source_file=file_path,
                item_count=item_count,
                errors=errors
            )
            
        except Exception as e:
            raise ParseError(str(e), file_path, line_number)
    
    def _parse_txt_delimited(self, file_path: str, 
                              delimiter: str = ',') -> ParsedData:
        """
        Parse a delimited TXT file (CSV/TSV style).
        
        Args:
            file_path: Path to the delimited file
            delimiter: Field delimiter
        
        Returns:
            ParsedData: Parsed delimited data
        """
        result_data = []
        errors = []
        line_number = 0
        headers = None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_number, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#') or line.startswith('//'):
                        continue
                    
                    fields = line.split(delimiter)
                    fields = [f.strip() for f in fields]
                    
                    if headers is None:
                        # First non-empty line is headers
                        headers = fields
                        continue
                    
                    # Create dictionary from fields
                    if len(fields) == len(headers):
                        row_data = dict(zip(headers, fields))
                        result_data.append(row_data)
                    else:
                        errors.append(
                            f"Line {line_number}: Field count mismatch "
                            f"(expected {len(headers)}, got {len(fields)})"
                        )
            
            item_count = len(result_data)
            logger.info(f"Parsed delimited file: {file_path} ({item_count} rows)")
            
            return ParsedData(
                format=FileFormat.TXT_CSV if delimiter == ',' else FileFormat.TXT_TSV,
                data=result_data,
                source_file=file_path,
                item_count=item_count,
                errors=errors
            )
            
        except Exception as e:
            raise ParseError(str(e), file_path, line_number)


# ============ Specialized Parsers ============

class CredentialsParser:
    """
    Specialized parser for credentials files.
    
    Expected format: email:password (one per line)
    """
    
    @staticmethod
    def parse(file_path: str) -> Dict[str, str]:
        """
        Parse a credentials file.
        
        Args:
            file_path: Path to credentials.txt
        
        Returns:
            dict: {email: password} mapping
        """
        credentials = {}
        
        if not os.path.exists(file_path):
            logger.warning(f"Credentials file not found: {file_path}")
            return credentials
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Try delimiters
                    for delim in [':', '=', ' ']:
                        if delim in line:
                            parts = line.split(delim, 1)
                            if len(parts) == 2:
                                email = parts[0].strip()
                                password = parts[1].strip()
                                
                                # Validate email format
                                if '@' in email and '.' in email:
                                    credentials[email] = password
                                else:
                                    logger.warning(
                                        f"Line {line_num}: Invalid email format: {email}"
                                    )
                                break
                            else:
                                logger.warning(
                                    f"Line {line_num}: Could not parse credentials line"
                                )
        
        except Exception as e:
            logger.error(f"Error parsing credentials: {e}")
        
        return credentials


class UserDataParser:
    """
    Specialized parser for user data JSON files.
    
    Expected format from users.json:
    {
        "email": {
            "sessions": {...},
            "active_session": "...",
            "theme": "dark",
            "personality": "default",
            "tier": "free",
            "image_usage": {...},
            "upgrade_history": [...]
        }
    }
    """
    
    @staticmethod
    def parse(file_path: str) -> Dict[str, Dict[str, Any]]:
        """
        Parse a user data JSON file.
        
        Args:
            file_path: Path to users.json
        
        Returns:
            dict: {email: user_data} mapping
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate structure
            if not isinstance(data, dict):
                raise ParseError("Expected JSON object", file_path)
            
            # Validate each user entry
            for email, user_data in data.items():
                if not isinstance(user_data, dict):
                    logger.warning(f"Skipping invalid user entry: {email}")
                    continue
                
                # Ensure required fields exist with defaults
                user_data.setdefault('sessions', {})
                user_data.setdefault('active_session', '')
                user_data.setdefault('theme', 'dark')
                user_data.setdefault('personality', 'default')
                user_data.setdefault('tier', 'free')
                user_data.setdefault('image_usage', {'last_reset': None, 'count': 0})
                user_data.setdefault('upgrade_history', [])
            
            logger.info(f"Parsed user data file: {file_path} ({len(data)} users)")
            return data
            
        except json.JSONDecodeError as e:
            raise ParseError(f"Invalid JSON: {e}", file_path, e.lineno)
    
    @staticmethod
    def extract_sessions(user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract session data from user data.
        
        Args:
            user_data: User data dictionary
        
        Returns:
            list: List of session dictionaries
        """
        sessions = []
        sessions_dict = user_data.get('sessions', {})
        
        for session_id, session_data in sessions_dict.items():
            if isinstance(session_data, dict):
                sessions.append({
                    'session_id': session_id,
                    'name': session_data.get('name', 'New Chat'),
                    'history': session_data.get('history', []),
                    'created': session_data.get('created', '')
                })
        
        return sessions


class RateLimitParser:
    """
    Specialized parser for rate limit JSON files.
    
    Expected format:
    {
        "identifier": {
            "request_count": 10,
            "window_start": "2026-01-01T00:00:00"
        }
    }
    """
    
    @staticmethod
    def parse(file_path: str) -> Dict[str, Dict[str, Any]]:
        """
        Parse a rate limits JSON file.
        
        Args:
            file_path: Path to rate_limits.json
        
        Returns:
            dict: {identifier: rate_limit_data} mapping
        """
        try:
            if not os.path.exists(file_path):
                logger.warning(f"Rate limits file not found: {file_path}")
                return {}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
                if not content:
                    return {}
                
                data = json.loads(content)
                
                if not isinstance(data, dict):
                    raise ParseError("Expected JSON object", file_path)
                
                return data
                
        except json.JSONDecodeError as e:
            raise ParseError(f"Invalid JSON: {e}", file_path, e.lineno)


# ============ Utility Functions ============

def parse_data_file(file_path: str, parser: Optional[FileParser] = None) -> ParsedData:
    """
    Convenience function to parse a data file.
    
    Args:
        file_path: Path to the file
        parser: Optional custom parser instance
    
    Returns:
        ParsedData: Parsed data
    """
    parser = parser or FileParser()
    return parser.parse_file(file_path)


def parse_all_files_in_directory(directory: str, 
                                  extensions: Optional[List[str]] = None) -> Dict[str, ParsedData]:
    """
    Parse all data files in a directory.
    
    Args:
        directory: Directory to scan
        extensions: File extensions to include (default: .json, .txt, .csv, .tsv)
    
    Returns:
        dict: {file_path: ParsedData} mapping
    """
    extensions = extensions or ['.json', '.txt', '.csv', '.tsv']
    results = {}
    
    for filename in os.listdir(directory):
        ext = os.path.splitext(filename)[1].lower()
        if ext in extensions:
            file_path = os.path.join(directory, filename)
            try:
                results[file_path] = parse_data_file(file_path)
            except Exception as e:
                logger.error(f"Failed to parse {file_path}: {e}")
                results[file_path] = ParsedData(
                    format=FileFormat.UNKNOWN,
                    data={},
                    source_file=file_path,
                    item_count=0,
                    errors=[str(e)]
                )
    
    return results


if __name__ == "__main__":
    # Test parsing
    import sys
    
    if len(sys.argv) > 1:
        parser = FileParser()
        result = parser.parse_file(sys.argv[1])
        print(f"Format: {result.format.value}")
        print(f"Items: {result.item_count}")
        print(f"Data: {json.dumps(result.data, indent=2)[:500]}")
        if result.errors:
            print(f"Errors: {result.errors}")
    else:
        print("Usage: python parser.py <file_path>")
