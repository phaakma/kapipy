import os
import sqlite3
import json
from datetime import datetime, timezone


class AuditManager:
    """
    Manages auditing for a GISK instance.

    Provides methods to record and retrieve information relating to interactions with the GISK.
    All data is stored in a SQLite database.
    """

    def __init__(self) -> None:
        """
        Initializes the AuditManager.
        """
        self.enabled = False
        self.folder = None
        self.retain_data = True
        self.db_name = "audit_db.sqlite"
        self.requests_table_name = "requests"

    def enable_auditing(self, folder: str, retain_data: bool = True) -> None:
        """
        Enable auditing and create the audit database if it does not exist.

        Parameters:
            folder (str): The directory where the audit database will be stored.
            retain_data (bool, optional): Whether to retain audit data. Defaults to True.
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
                    total_features INTEGER
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
        response: dict = None,
    ) -> None:
        """
        Adds a request record to the audit database.

        Converts request_headers and request_params dicts to JSON strings for storage.

        Parameters:
            item_id (int): The ID of the item involved in the request.
            item_kind (str): The kind of the item (e.g., 'vector', 'table').
            item_type (str): The type of the item.
            request_type (str): The type of request (e.g., 'GET', 'POST').
            request_url (str): The URL of the request.
            request_method (str): The HTTP method used for the request.
            request_time (datetime): The time the request was made.
            request_headers (dict): The headers sent with the request.
            request_params (dict): The parameters sent with the request.
            response (dict, optional): The response received from the request.

        Returns:
            None
        """

        # Silently return without doing anything if auditing is not enabled.
        if self.enabled is False:
            return False

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

        total_features = response.get("totalFeatures") if response else None

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
                    total_features
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    item_kind,
                    item_type,
                    request_type,
                    request_url,
                    request_method,
                    request_time_str,
                    (
                        json.dumps(request_headers)
                        if isinstance(request_headers, dict)
                        else str(request_headers)
                    ),
                    (
                        json.dumps(request_params)
                        if isinstance(request_params, dict)
                        else str(request_params)
                    ),
                    total_features,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        if response:
            self.save_data(item_id, request_type, request_time, response)

    def get_latest_request_for_item(
        self, item_id: int, request_type: str = None
    ) -> dict | None:
        """
        Returns the most recent audit record for the given item_id, optionally filtered by request_type,
        based on request_time.

        Parameters:
            item_id (int): The ID of the item to search for.
            request_type (str, optional): The type of request to filter by.

        Returns:
            dict or None: The most recent audit record as a dictionary, or None if no record is found.
        """

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

    def save_data(
        self, item_id: int, request_type: str, request_time: datetime, data: dict
    ) -> None:
        """
        Save the audit data to a local JSON file.

        The file will be saved in a 'data' subfolder within the audit folder, with a filename
        formatted as '{request_type}_{item_id}_{request_time}.json'.

        Parameters:
            item_id (int): The ID of the item related to the data.
            request_type (str): The type of request (e.g., 'GET', 'POST').
            request_time (str): The time the request was made, used in the filename.
            data (dict): The data to be saved as JSON.

        Returns:
            None

        Raises:
            OSError: If the file or directory cannot be created or written.
            TypeError: If the data cannot be serialized to JSON.
        """
        data_folder = os.path.join(self.folder, "data")
        os.makedirs(data_folder, exist_ok=True)
        request_time_str = request_time.strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(
            data_folder, f"{request_type}_{item_id}_{request_time_str}.json"
        )
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=None, separators=(",", ":"))

    def __repr__(self) -> str:
        """
        Returns an unambiguous string representation of the AuditManager instance.

        Returns:
            str: String representation of the AuditManager.
        """
        return f"AuditManager()"

    def __str__(self) -> str:
        """
        Returns a user-friendly string representation of the AuditManager instance.

        Returns:
            str: User-friendly string representation.
        """
        if self.enabled:
            return f"AuditManager, enabled, {self.folder}, {self.db_name}"
        return f"AuditManager"
