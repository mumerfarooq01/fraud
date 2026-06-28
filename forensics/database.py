import sqlite3
import os
import hashlib
from datetime import datetime
from pathlib import Path

class ForensicDatabase:
    """
    SQLite database to track NOA identification numbers and detect duplicates
    """
    
    def __init__(self, db_path='forensic_records.db'):
        """Initialize database connection"""
        self.db_path = db_path
        self._create_tables()
    
    def _create_tables(self):
        """Create tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS noa_ids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                identification_number TEXT NOT NULL UNIQUE,
                sin_last_4 TEXT,
                full_name TEXT,
                date_issued TEXT,
                uploaded_timestamp TEXT,
                document_hash TEXT,
                file_name TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS duplicate_detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                identification_number TEXT NOT NULL,
                original_record_id INTEGER,
                duplicate_file_name TEXT,
                detected_timestamp TEXT,
                FOREIGN KEY (original_record_id) REFERENCES noa_ids(id)
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_identification_number 
            ON noa_ids(identification_number)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_sin 
            ON noa_ids(sin_last_4)
        ''')
        
        conn.commit()
        conn.close()
    
    def check_duplicate_id(self, identification_number):
        """
        Check if identification number already exists
        
        Returns:
            dict with {
                'is_duplicate': bool,
                'original_record': dict or None
            }
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM noa_ids 
            WHERE identification_number = ?
        ''', (identification_number,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'is_duplicate': True,
                'original_record': {
                    'id': result[0],
                    'identification_number': result[1],
                    'sin_last_4': result[2],
                    'full_name': result[3],
                    'date_issued': result[4],
                    'uploaded_timestamp': result[5],
                    'file_name': result[7]
                }
            }
        else:
            return {
                'is_duplicate': False,
                'original_record': None
            }
    
    def store_id_number(self, identification_number, sin_last_4=None, full_name=None,
                       date_issued=None, document_hash=None, file_name=None):
        """
        Store a new identification number
        
        Returns:
            bool: True if stored, False if duplicate
        """
        # Check if already exists
        check_result = self.check_duplicate_id(identification_number)
        if check_result['is_duplicate']:
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO noa_ids 
                (identification_number, sin_last_4, full_name, date_issued, 
                 uploaded_timestamp, document_hash, file_name)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                identification_number,
                sin_last_4,
                full_name,
                date_issued,
                datetime.now().isoformat(),
                document_hash,
                file_name
            ))
            
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def record_duplicate_detection(self, identification_number, duplicate_file_name):
        """Record when a duplicate ID is detected"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get original record ID
        cursor.execute('''
            SELECT id FROM noa_ids WHERE identification_number = ?
        ''', (identification_number,))
        
        original_id = cursor.fetchone()
        
        if original_id:
            cursor.execute('''
                INSERT INTO duplicate_detections
                (identification_number, original_record_id, duplicate_file_name, detected_timestamp)
                VALUES (?, ?, ?, ?)
            ''', (
                identification_number,
                original_id[0],
                duplicate_file_name,
                datetime.now().isoformat()
            ))
            
            conn.commit()
        
        conn.close()
    
    def get_all_records(self):
        """Get all stored identification numbers"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM noa_ids ORDER BY created_at DESC')
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def get_duplicate_history(self):
        """Get all duplicate detection records"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT d.*, n.full_name, n.sin_last_4
            FROM duplicate_detections d
            LEFT JOIN noa_ids n ON d.original_record_id = n.id
            ORDER BY d.detected_timestamp DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return results

