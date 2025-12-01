from __future__ import annotations
from typing import Optional, Literal
from aiosqlite import Connection as AioConnection


class PathConnection:
    """
    PathConnection is a class that represents a connection to a database file, 
    allowing for optional aliasing and management of the connection in dictionaries.
    
    Supports separate read and write connections for improved concurrency.
    The `conn` property is an alias for `write_conn` for backwards compatibility.
    
    Attributes:
        path (str): The file path to the database.
        alias (Optional[str]): An optional alias for the connection.
        write_conn (AioConnection): The write connection object.
        read_conn (Optional[AioConnection]): The read connection object.
        conn (AioConnection): Alias for write_conn (backwards compatibility).
    Methods:
        get_conn(mode: str) -> Optional[AioConnection]:
            Returns the connection for the given mode ("read" or "write").
        __repr__() -> str:
            Returns a string representation of the PathConnection object.
        __eq__(value) -> bool:
            Compares two PathConnection objects for equality based on their paths.
        __hash__() -> int:
            Returns the hash of the PathConnection object based on its path.
        __bool__() -> bool:
            Returns True if the path attribute is non-empty, otherwise False.
    """
    

    def __init__(
        self,
        path: str,
        write_conn: AioConnection,
        read_conn: Optional[AioConnection] = None,
        alias: Optional[str] = None
    ) -> None:
        self.path = path
        self.alias = alias
        self.write_conn = write_conn
        self.read_conn = read_conn

    @property
    def conn(self) -> AioConnection:
        """Alias for write_conn for backwards compatibility."""
        return self.write_conn
    
    @conn.setter
    def conn(self, value: AioConnection) -> None:
        """Alias for write_conn for backwards compatibility."""
        self.write_conn = value

    def get_conn(self, mode: Literal["read", "write"] = "write") -> AioConnection:
        """
        Get the connection for the specified mode.
        
        Args:
            mode: "read" or "write", defaults to "write"
            
        Returns:
            The connection for the specified mode.
            For "read" mode, falls back to write_conn if read_conn is None.
        """
        if mode == "read":
            return self.read_conn if self.read_conn is not None else self.write_conn
        return self.write_conn

    def __repr__(self) -> str:
        return f"PathConnection(path={self.path}, alias={self.alias}, write_conn={self.write_conn}, read_conn={self.read_conn})"

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

    Methods:
        get_path_connection(path_or_alias: str) -> Optional[PathConnection]:
            Retrieves a PathConnection using a path or alias.
        get_connection(path_or_alias: str, mode: str) -> Optional[AioConnection]:
            Retrieves a connection using a path or alias and mode.
        __getitem__(key: str) -> PathConnection:
            Returns the PathConnection for the specified key.
        __contains__(key: str | PathConnection) -> bool:
            Checks if a path or alias exists.
        get(key: str, default: Optional[PathConnection] = None) -> Optional[PathConnection]:
            Returns the PathConnection if it exists, otherwise returns the default.
        __setitem__(key: str | PathConnection, value: PathConnection | AioConnection) -> None:
            Adds or updates a PathConnection.
        __delitem__(key: str) -> None:
            Removes the PathConnection by its path or alias.
        setalias(key: str, new_alias: Optional[str]) -> None:
            Assigns a new alias to an existing path.
        setpath(old_key: str, new_path: str) -> None:
            Changes the path associated with a connection.
        paths -> list[str]:
            Returns a list of all registered paths.
    """

    def __init__(self) -> None:
        self.path_connections: set[PathConnection] = set()
        self._key_to_pc: dict[str, PathConnection] = {}

    def _update_key_mapping(self, pc: PathConnection) -> None:
        """Update the key-to-PathConnection mapping for a PathConnection."""
        self._key_to_pc[pc.path] = pc
        if pc.alias:
            self._key_to_pc[pc.alias] = pc

    def _remove_key_mapping(self, pc: PathConnection) -> None:
        """Remove the key-to-PathConnection mapping for a PathConnection."""
        self._key_to_pc.pop(pc.path, None)
        if pc.alias:
            self._key_to_pc.pop(pc.alias, None)

    def get_path_connection(self, path_or_alias: str) -> Optional[PathConnection]:
        """
        Get the PathConnection associated with a given path or alias.
        """
        return self._key_to_pc.get(path_or_alias)

    def get_connection(
        self,
        path_or_alias: str,
        mode: Literal["read", "write"] = "write"
    ) -> Optional[AioConnection]:
        """
        Get the connection associated with a given path or alias.
        
        Args:
            path_or_alias: The path or alias of the database.
            mode: "read" or "write", defaults to "write" for backwards compatibility.
            
        Returns:
            The connection for the specified mode, or None if not found.
        """
        pc = self.get_path_connection(path_or_alias)
        if pc is None:
            return None
        return pc.get_conn(mode)

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

    def __getitem__(self, key: str) -> PathConnection:
        self._check_key(key)
        pc = self._key_to_pc.get(key)
        if pc is None:
            raise KeyError(f"No connection for '{key}'.")
        return pc

    def __contains__(self, key: str | PathConnection) -> bool:
        """
        Check if a database path or alias exists in the dictionary.
        """
        if key is None:
            return False
        if isinstance(key, str):
            return key in self._key_to_pc
        elif isinstance(key, PathConnection):
            return key.path in self._key_to_pc or (key.alias is not None and key.alias in self._key_to_pc)
        return False

    def get(self, key: str, default: Optional[PathConnection] = None) -> Optional[PathConnection]:
        return self._key_to_pc.get(key, default)

    def __setitem__(self, key: str | PathConnection, value: PathConnection | AioConnection) -> None:
        """
        Set or replace a PathConnection using a path or alias as the key.
        
        Args:
            key: Path string, alias string, or PathConnection.
            value: PathConnection or AioConnection. If AioConnection, it will be
                   used as the write_conn.
        """
        self._check_key(key)
        
        # Handle value being either PathConnection or AioConnection
        if isinstance(value, PathConnection):
            new_pc = value
        elif isinstance(value, AioConnection):
            # Create a new PathConnection with the connection as write_conn
            path = key.path if isinstance(key, PathConnection) else key
            new_pc = PathConnection(path=path, write_conn=value)
        else:
            raise ValueError("Value must be PathConnection or aiosqlite.Connection.")

        # Try to update existing PathConnection
        preserved_alias = None
        for pc in list(self.path_connections):
            if key == pc.path or key == pc.alias or (isinstance(key, PathConnection) and key.path == pc.path):
                self._remove_key_mapping(pc)
                self.path_connections.remove(pc)
                # Preserve alias if not specified in new_pc
                if new_pc.alias is None and pc.alias is not None:
                    preserved_alias = pc.alias
                break

        # If we need to preserve an alias, create a new PathConnection with it
        if preserved_alias is not None:
            new_pc = PathConnection(
                path=new_pc.path,
                write_conn=new_pc.write_conn,
                read_conn=new_pc.read_conn,
                alias=preserved_alias
            )

        self.path_connections.add(new_pc)
        self._update_key_mapping(new_pc)

    def __delitem__(self, key: str | PathConnection) -> None:
        """
        Delete a PathConnection by path or alias.
        """
        self._check_key(key)
        search_key = key.path if isinstance(key, PathConnection) else key
        
        to_remove = None
        for pc in self.path_connections:
            if search_key == pc.path or search_key == pc.alias:
                to_remove = pc
                break

        if to_remove is None:
            raise KeyError(f"Database path or alias '{search_key}' not found.")

        self._remove_key_mapping(to_remove)
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
            if new_alias in self._key_to_pc:
                raise KeyError(f"Alias '{new_alias}' already exists.")

        # Locate the PathConnection
        target = self._key_to_pc.get(key)

        if target is None:
            raise KeyError(f"Key '{key}' not found.")

        # Remove old alias mapping if it exists
        if target.alias and target.alias in self._key_to_pc:
            del self._key_to_pc[target.alias]

        # Update alias
        target.alias = new_alias
        if new_alias:
            self._key_to_pc[new_alias] = target

    def setpath(self, old_key: str, new_path: str) -> None:
        """
        Change the path for an existing PathConnection.
        The old key can be a path or alias. The new path must be unused.
        """
        self._check_key(old_key)
        self._check_key(new_path)

        if new_path in self._key_to_pc:
            raise KeyError(f"New path '{new_path}' already exists.")

        # Locate the target PathConnection
        target = self._key_to_pc.get(old_key)

        if target is None:
            raise KeyError(f"No entry found for '{old_key}'.")

        # Update internal state
        self._remove_key_mapping(target)
        self.path_connections.remove(target)

        target.path = new_path
        self.path_connections.add(target)
        self._update_key_mapping(target)

    @property
    def paths(self) -> list[str]:
        """
        Get a list of all paths in the dictionary.
        """
        return [pc.path for pc in self.path_connections]