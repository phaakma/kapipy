"""
base_item.py
A base class to represent an item.
"""


class BaseItem:
    """
    Base class for representing an item in the Koordinates system.

    This class provides a structure for items that can be extended by specific item types.
    It stores basic metadata and provides dynamic attribute access.

    Attributes:
        _gis (GIS): The GIS instance this item belongs to.
        _raw_json (dict): The raw JSON dictionary representing the item.
        id (str): The unique identifier of the item.
        url (str): The URL of the item.
        type (str): The type of the item (e.g., 'layer', 'table').
        kind (str): The kind of the item (e.g., 'vector', 'table').
        title (str): The title of the item.
        description (str): The description of the item.
        _jobs (list): List of JobResult objects associated with this item.
    """

    def __init__(self, gis: "GIS", item_dict: dict) -> None:
        """
        Initializes the BaseItem instance from a dictionary returned from the API.

        Parameters:
            gis (GIS): The GIS instance that this item belongs to.
            item_dict (dict): A dictionary containing the item's details, typically from an API response.

        Returns:
            None
        """

        self._gis = gis
        self._raw_json = item_dict
        self.id = item_dict.get("id")
        self.url = item_dict.get("url")
        self.type = item_dict.get("type")
        self.kind = item_dict.get("kind")
        self.title = item_dict.get("title")
        self.description = item_dict.get("description")
        self._jobs = []

    def __getattr__(self, item) -> object:
        """
        Provides dynamic attribute access for the item.

        Parameters:
            item (str): The name of the attribute to access.

        Returns:
            object: The value of the requested attribute.

        Raises:
            AttributeError: If the attribute does not exist in the item.
        """

        attr = self._raw_json.get(item, None)
        if attr is None:
            raise AttributeError(f"{self.__class__.__name__} has no attribute '{item}'")
        return attr

    def __repr__(self) -> str:
        """
        Returns an unambiguous string representation of the BaseItem instance.

        Returns:
            str: String representation of the BaseItem.
        """
        return f"BaseItem(id={self.id!r}, title={self.title!r}, type={self.type!r})"

    def __str__(self) -> str:
        """
        Returns a user-friendly string representation of the BaseItem instance.

        Returns:
            str: User-friendly string representation.
        """
        return f"{self.title or 'Unnamed Item'} (ID: {self.id}, Type: {self.type})"
