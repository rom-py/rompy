from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any


class TransferBase(ABC):
    """
    Abstract base class defining the transfer interface for ROMPy.
    Concrete schemes (e.g., local file, s3, http) will implement these methods.
    """

    @abstractmethod
    def get(
        self, uri: str, destdir: Path, name: Optional[str] = None, link: bool = False
    ) -> Path:
        """
        Retrieve data from the given URI and place it under destdir.
        Returns the final Path to the retrieved object.
        """
        raise NotImplementedError

    @abstractmethod
    def exists(self, uri: str) -> bool:
        """
        Return True if the given URI exists in the transfer store.
        """
        raise NotImplementedError

    @abstractmethod
    def list(self, uri: str) -> List[str]:
        """
        List items under the given URI and return a list of their names/paths.
        """
        raise NotImplementedError

    @abstractmethod
    def put(self, local_path: Path, uri: str) -> str:
        """
        Upload or copy a local file to the given URI.
        Returns the URI that was created.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, uri: str, recursive: bool = False) -> None:
        """
        Delete the resource at the given URI.
        If recursive is True, delete recursively.
        """
        raise NotImplementedError

    @abstractmethod
    def stat(self, uri: str) -> Dict[str, Any]:
        """
        Return a dictionary with metadata about the given URI.
        """
        raise NotImplementedError
