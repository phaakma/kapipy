import os
import sqlite3
from datetime import datetime, timezone


class AuditManager:
    """
    Manages auditing for a GISK instance.

    Provides methods to record and retrieve information relating to interactions with the GISK.
    All data is stored in a SQLite database.

    Attributes:
        _gis (GISK): The GISK instance this manager is associated with.
    """

    def __init__(self, gis: "GISK") -> None:
        """
        Initializes the ContentManager with a GISK instance.

        Parameters:
            gis (GISK): The GISK instance to manage content for.
        """
        self._gis = gis
        self.enabled = False
        self.folder = None
        self.retain_data = True
        self.db_name = "audit_db.sqlite"
        self.requests_table_name = "requests"

    def enable_auditing(self, folder: str, retain_data: bool = True) -> None:
        """
        Enable auditing.
        """
        self.enabled = True
        self.folder = folder
        self.retain_data = retain_data
        self.__create_database()

    def disable_auditing(self):
        """
        Disable auditing.
        """
        self.enabled = False

    def __create_database(self):
        """
        Creates the SQLite database and the audit table if they do not already exist.

        Uses:
            self.db_name: Name of the database file.
            self.filepath: Directory where the database file is stored.
            self.requests_table_name: Name of the audit table.

        The audit table should have the following fields:
            - id (INTEGER PRIMARY KEY AUTOINCREMENT)
            - item_id (INTEGER)
            - item_kind (TEXT)
            - item_type (TEXT)
            - request_type (TEXT)
            - request_url (TEXT)
            - request_method (TEXT)
            - request_time (TEXT)
            - request_headers (TEXT)
            - request_params (TEXT)
            - total_features (TEXT)
            - adds (INTEGER)
            - updates (INTEGER)
            - deletes (INTEGER)
        Creates an index on item_id and request_time.
        """
        db_path = os.path.join(self.folder, self.db_name)
        os.makedirs(self.folder, exist_ok=True)
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.requests_table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER,
                    item_kind TEXT,
                    item_type TEXT,
                    request_type TEXT,
                    request_url TEXT,
                    request_method TEXT,
                    request_time TEXT,
                    request_headers TEXT,
                    request_params TEXT,
                    total_features INTEGER,
                    adds INTEGER,
                    updates INTEGER,
                    deletes INTEGER
                )
            """
            )
            cursor.execute(
                f"""
                CREATE INDEX IF NOT EXISTS idx_{self.requests_table_name}_item_id
                ON {self.requests_table_name} (item_id)
            """
            )
            cursor.execute(
                f"""
                CREATE INDEX IF NOT EXISTS idx_{self.requests_table_name}_request_time
                ON {self.requests_table_name} (request_time)
            """
            )
            conn.commit()
        finally:
            conn.close()

    def add_request_record(
        self,
        item_id: int,
        item_kind: str,
        item_type: str,
        request_type: str,
        request_url: str,
        request_method: str,
        request_time: datetime,
        request_headers: dict,
        request_params: dict,
        total_features: int = None,
        adds: int = None,
        updates: int = None,
        deletes: int = None,
    ) -> None:
        """
        Adds a request record to the audit database.
        Converts request_headers and request_params dicts to JSON strings for storage.
        """

        # Silently return without doing anything if auditing is not enabled.
        if self.enabled is False:
            return False 

        import sqlite3
        import json

        if isinstance(request_time, datetime):
            # Convert to UTC if not already
            if request_time.tzinfo is None:
                request_time_utc = request_time.replace(tzinfo=timezone.utc)
            else:
                request_time_utc = request_time.astimezone(timezone.utc)
            # Format as ISO string without timezone info
            request_time_str = request_time_utc.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            request_time_str = str(request_time)

        db_path = os.path.join(self.folder, self.db_name)
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                INSERT INTO {self.requests_table_name} (
                    item_id,
                    item_kind,
                    item_type,
                    request_type,
                    request_url,
                    request_method,
                    request_time,
                    request_headers,
                    request_params,
                    total_features,
                    adds,
                    updates,
                    deletes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    item_kind,
                    item_type,
                    request_type,
                    request_url,
                    request_method,
                    request_time_str,
                    json.dumps(request_headers) if isinstance(request_headers, dict) else str(request_headers),
                    json.dumps(request_params) if isinstance(request_params, dict) else str(request_params),
                    total_features,
                    adds,
                    updates,
                    deletes,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    # def get_latest_request_for_item(self, item_id: int) -> dict | None:
    #     """
    #     Returns the most recent audit record for the given item_id, based on request_time.
    #     Returns None if no record is found.
    #     """
    #     import sqlite3

    #     db_path = os.path.join(self.folder, self.db_name)
    #     conn = sqlite3.connect(db_path)
    #     try:
    #         cursor = conn.cursor()
    #         cursor.execute(
    #             f"""
    #             SELECT *
    #             FROM {self.requests_table_name}
    #             WHERE item_id = ?
    #             ORDER BY request_time DESC
    #             LIMIT 1
    #             """,
    #             (item_id,),
    #         )
    #         row = cursor.fetchone()
    #         if row is None:
    #             return None
    #         # Get column names for dict conversion
    #         col_names = [desc[0] for desc in cursor.description]
    #         return dict(zip(col_names, row))
    #     finally:
    #         conn.close()

    def get_latest_request_for_item(self, item_id: int, request_type: str = None) -> dict | None:
        """
        Returns the most recent audit record for the given item_id, optionally filtered by request_type,
        based on request_time. Returns None if no record is found.
        """
        import sqlite3

        db_path = os.path.join(self.folder, self.db_name)
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            if request_type is not None:
                cursor.execute(
                    f"""
                    SELECT *
                    FROM {self.requests_table_name}
                    WHERE item_id = ? AND request_type = ?
                    ORDER BY request_time DESC
                    LIMIT 1
                    """,
                    (item_id, request_type),
                )
            else:
                cursor.execute(
                    f"""
                    SELECT *
                    FROM {self.requests_table_name}
                    WHERE item_id = ?
                    ORDER BY request_time DESC
                    LIMIT 1
                    """,
                    (item_id,),
                )
            row = cursor.fetchone()
            if row is None:
                return None
            col_names = [desc[0] for desc in cursor.description]
            return dict(zip(col_names, row))
        finally:
            conn.close()

    def __repr__(self) -> str:
        """
        Returns an unambiguous string representation of the AuditManager instance.

        Returns:
            str: String representation of the ContentManager.
        """
        return f"AuditManager(gis={repr(self._gis)})"

    def __str__(self) -> str:
        """
        Returns a user-friendly string representation of the AuditManager instance.

        Returns:
            str: User-friendly string representation.
        """
        return f"AuditManager for GISK: {getattr(self._gis, 'name', None) or getattr(self._gis, 'url', 'Unknown')}"
