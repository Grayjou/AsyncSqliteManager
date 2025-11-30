from __future__ import annotations
from typing import Optional
from aiosqlite import Connection as AioConnection


class PathConnection:
    """
    PathConnection is a class that represents a connection to a database file, 
    allowing for optional aliasing and management of the connection in dictionaries.
    Attributes:
        path (str): The file path to the database.
        alias (Optional[str]): An optional alias for the connection.
        conn (AioConnection): The database connection object.
    Methods:
        conn_dict() -> dict[str, AioConnection]:
            Returns a dictionary representation of the connection, 
            including the alias if provided.
        __repr__() -> str:
            Returns a string representation of the PathConnection object.
        del_from(dictionary: dict[str, AioConnection]) -> None:
            Removes the connection (by path and alias, if applicable) 
            from the given dictionary.
        update_to(dictionary: dict[str, AioConnection]) -> None:
            Updates the given dictionary with the connection 
            (by path and alias, if applicable).
        __eq__(value) -> bool:
            Compares two PathConnection objects for equality based on their paths.
        __hash__() -> int:
            Returns the hash of the PathConnection object based on its path.
        __bool__() -> bool:
            Returns True if the path attribute is non-empty, otherwise False.
    """
    

    def __init__(self, path: str, conn: AioConnection, alias: Optional[str] = None) -> None:
        self.path = path
        self.alias = alias
        self.conn = conn
    def conn_dict(self) -> dict[str, AioConnection]:
        return {self.path: self.conn,
                self.alias: self.conn} if self.alias is not None else {self.path: self.conn}
    def __repr__(self) -> str:
        return f"PathConnection(path={self.path}, alias={self.alias}, conn={self.conn})"
    def del_from(self, dictionary: dict[str, AioConnection]) -> None:
        """
        Remove the connection from the dictionary.
        """
        dictionary.pop(self.path, None)
        if self.alias:
            dictionary.pop(self.alias, None)
    def update_to(self, dictionary: dict[str, AioConnection]) -> None:
        """
        Update the connection in the dictionary.
        """
        dictionary.update(self.conn_dict())
    def __eq__(self, value) -> bool:
        return isinstance(value, PathConnection) and self.path == value.path
    def __hash__(self) -> int:
        return hash(self.path)
    def __bool__(self) -> bool:
        return bool(self.path)


class DbPathDict:
    """
    A dictionary-like structure that manages multiple PathConnection objects,
    allowing access to SQLite connections via paths or aliases.

    Attributes:
        path_connections (Set[PathConnection]): A set of PathConnection instances.
        conn_dict (dict[str, AioConnection]): A mapping from path or alias to AioConnection objects.

    Methods:
        get_connection(path_or_alias: str) -> Optional[AioConnection]:
            Retrieves a connection using a path or alias.
        __getitem__(key: str) -> AioConnection:
            Returns the connection for the specified key.
        __contains__(key: str | PathConnection) -> bool:
            Checks if a path or alias exists.
        get(key: str, default: Optional[AioConnection] = None) -> Optional[AioConnection]:
            Returns the connection if it exists, otherwise returns the default.
        __setitem__(key: str | PathConnection, conn: AioConnection) -> None:
            Adds or updates a connection.
        __delitem__(key: str) -> None:
            Removes the connection by its path or alias.
        setalias(key: str, new_alias: Optional[str]) -> None:
            Assigns a new alias to an existing path.
        setpath(old_key: str, new_path: str) -> None:
            Changes the path associated with a connection.
        paths -> list[str]:
            Returns a list of all registered paths.
    """

    def __init__(self) -> None:
        self.path_connections: set[PathConnection] = set()
        self.conn_dict: dict[str, AioConnection] = {}
    def get_connection(self,path_or_alias: str) -> Optional[AioConnection]:
        """
        Get the connection associated with a given path or alias.
        """
        if path_or_alias in self.conn_dict:
            return self.conn_dict[path_or_alias]
        else:
            return None
    @staticmethod
    def _check_key(key: str | PathConnection) -> None:
        """
        Check if the key is a valid string or PathConnection.
        """
        if isinstance(key, PathConnection):
            if not key.path:
                raise ValueError("Path cannot be empty.")
            return
        if not isinstance(key, str):
            raise ValueError("Key must be a string or PathConnection.")
        if not key:
            raise ValueError("Path/alias cannot be empty.")

    def __getitem__(self, key: str) -> AioConnection:
        self._check_key(key)
        if key not in self.conn_dict:
            raise KeyError(f"No connection for '{key}'.")
        return self.conn_dict[key]
    def __contains__(self, key: str | PathConnection) -> bool:
        """
        Check if a database path or alias exists in the dictionary.
        """
        if key is None:
            return False
        if isinstance(key, str):
            return key in self.conn_dict
        elif isinstance(key, PathConnection):
            return key.path in self.conn_dict or (key.alias is not None and key.alias in self.conn_dict)
        return False
    def get(self, key: str, default=None) -> Optional[AioConnection]:
        return self.conn_dict.get(key, default)
    def __setitem__(self, key: str | PathConnection, conn: AioConnection) -> None:
        """
        Set or replace a connection using a path or alias as the key.
        If the key matches an existing PathConnection (by path or alias), it replaces the connection.
        If not, it creates a new PathConnection with the key as path and no alias.
        """
        self._check_key(key)
        if not isinstance(conn, AioConnection):
            raise ValueError("Value must be aiosqlite.Connection.")

        # Try to update existing PathConnection
        for pc in self.path_connections:
            if key == pc.path or key == pc.alias:
                pc.conn = conn
                pc.update_to(self.conn_dict)
                return


        # Otherwise add new PC
        if isinstance(key, str):
            pc = PathConnection(key, conn)
            pc.update_to(self.conn_dict)
            self.path_connections.add(pc)
        else:
            key.update_to(self.conn_dict)
            self.path_connections.add(key)
    def __delitem__(self, key: str | PathConnection) -> None:
        """
        Delete a PathConnection by path or alias.
        """
        self._check_key(key)
        to_remove = None
        if isinstance(key, PathConnection):
            key = key.path
        for pc in self.path_connections:
            if key == pc.path or key == pc.alias:
                to_remove = pc
                break

        if to_remove is None:
            raise KeyError(f"Database path or alias '{key}' not found.")

        to_remove.del_from(self.conn_dict)
        self.path_connections.remove(to_remove)


        
    def setalias(self, key: str, new_alias: Optional[str]) -> None:
        """
        Set or update the alias for an existing PathConnection.
        
        Args:
            key (str): Existing path or alias.
            new_alias (Optional[str]): New alias to assign. Can be None to remove alias.

        Raises:
            KeyError: If the key is not found or new_alias already exists.
            ValueError: If new_alias is an invalid string.
        """
        self._check_key(key)
        if new_alias is not None:
            self._check_key(new_alias)
            if new_alias in self.conn_dict:
                raise KeyError(f"Alias '{new_alias}' already exists.")

        # Locate the PathConnection
        target = None
        for pc in self.path_connections:
            if key == pc.path or key == pc.alias:
                target = pc
                break

        if target is None:
            raise KeyError(f"Key '{key}' not found.")

        # Remove old alias if it exists
        if target.alias and target.alias in self.conn_dict:
            del self.conn_dict[target.alias]

        # Update alias
        target.alias = new_alias
        target.update_to(self.conn_dict)

    def setpath(self, old_key: str, new_path: str) -> None:
        """
        Change the path for an existing PathConnection.
        The old key can be a path or alias. The new path must be unused.
        """
        self._check_key(old_key)
        self._check_key(new_path)

        if new_path in self.conn_dict:
            raise KeyError(f"New path '{new_path}' already exists.")

        # Locate the target PathConnection
        target = None
        for pc in self.path_connections:
            if old_key == pc.path or old_key == pc.alias:
                target = pc
                break

        if target is None:
            raise KeyError(f"No entry found for '{old_key}'.")

        # Update internal state
        target.del_from(self.conn_dict)
        self.path_connections.remove(target)

        target.path = new_path
        target.update_to(self.conn_dict)
        self.path_connections.add(target)
    @property
    def paths(self) -> list[str]:
        """
        Get a list of all paths in the dictionary.
        """
        return [pc.path for pc in self.path_connections]