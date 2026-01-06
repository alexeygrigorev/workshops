import io
import zipfile
import traceback

from dataclasses import dataclass
from typing import Iterable, Callable, Any, Dict, List

import requests
import frontmatter


@dataclass
class RawRepositoryFile:
    filename: str
    content: str


class GithubRepositoryDataReader:
    """
    Downloads and parses markdown and code files from a GitHub repository.
    """

    def __init__(self,
                repo_owner: str,
                repo_name: str,
                allowed_extensions: Iterable[str] | None = None,
                filename_filter: Callable[[str], bool] | None = None
        ):
        """
        Initialize the GitHub repository data reader.
        
        Args:
            repo_owner: The owner/organization of the GitHub repository
            repo_name: The name of the GitHub repository
            allowed_extensions: Optional set of file extensions to include
                    (e.g., {"md", "py"}). If not provided, all file types are included
            filename_filter: Optional callable to filter files by their path
        """
        prefix = "https://codeload.github.com"
        self.url = (
            f"{prefix}/{repo_owner}/{repo_name}/zip/refs/heads/main"
        )

        if allowed_extensions is not None:
            self.allowed_extensions = {ext.lower() for ext in allowed_extensions}

        if filename_filter is None:
            self.filename_filter = lambda filepath: True
        else:
            self.filename_filter = filename_filter

    def read(self) -> list[RawRepositoryFile]:
        """
        Download and extract files from the GitHub repository.
        
        Returns:
            List of RawRepositoryFile objects for each processed file
            
        Raises:
            Exception: If the repository download fails
        """
        resp = requests.get(self.url)
        if resp.status_code != 200:
            raise Exception(f"Failed to download repository: {resp.status_code}")

        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        repository_data = self._extract_files(zf)
        zf.close()

        return repository_data

    def _extract_files(self, zf: zipfile.ZipFile) -> list[RawRepositoryFile]:
        """
        Extract and process files from the zip archive.
        
        Args:
            zf: ZipFile object containing the repository data

        Returns:
            List of RawRepositoryFile objects for each processed file
        """
        data = []

        for file_info in zf.infolist():
            filepath = self._normalize_filepath(file_info.filename)

            if self._should_skip_file(filepath):
                continue

            try:
                with zf.open(file_info) as f_in:
                    content = f_in.read().decode("utf-8", errors="ignore")
                    if content is not None:
                        content = content.strip()

                    file = RawRepositoryFile(
                        filename=filepath,
                        content=content
                    )
                    data.append(file)

            except Exception as e:
                print(f"Error processing {file_info.filename}: {e}")
                traceback.print_exc()
                continue

        return data

    def _should_skip_file(self, filepath: str) -> bool:
        """
        Determine whether a file should be skipped during processing.
        
        Args:
            filepath: The file path to check
            
        Returns:
            True if the file should be skipped, False otherwise
        """
        filepath = filepath.lower()

        # directory
        if filepath.endswith("/"):
            return True

        # hidden file
        filename = filepath.split("/")[-1]
        if filename.startswith("."):
            return True

        if self.allowed_extensions:
            ext = self._get_extension(filepath)
            if ext not in self.allowed_extensions:
                return True

        if not self.filename_filter(filepath):
            return True

        return False

    def _get_extension(self, filepath: str) -> str:
        """
        Extract the file extension from a filepath.
        
        Args:
            filepath: The file path to extract extension from
            
        Returns:
            The file extension (without dot) or empty string if no extension
        """
        filename = filepath.lower().split("/")[-1]
        if "." in filename:
            return filename.rsplit(".", maxsplit=1)[-1]
        else:
            return ""

    def _normalize_filepath(self, filepath: str) -> str:
        """
        Removes the top-level directory from the file path inside the zip archive.
        'repo-main/path/to/file.py' -> 'path/to/file.py'
        
        Args:
            filepath: The original filepath from the zip archive
            
        Returns:
            The normalized filepath with top-level directory removed
        """
        parts = filepath.split("/", maxsplit=1)
        if len(parts) > 1:
            return parts[1]
        else:
            return parts[0]


def read_github_data():
    repo_owner = 'evidentlyai'
    repo_name = 'docs'
    
    allowed_extensions = {"md", "mdx"}

    reader = GithubRepositoryDataReader(
        repo_owner,
        repo_name,
        allowed_extensions=allowed_extensions,
    )
    
    return reader.read()


def parse_data(data_raw):
    data_parsed = []
    for f in data_raw:
        post = frontmatter.loads(f.content)
        data = post.to_dict()
        data['filename'] = f.filename
        data_parsed.append(data)

    return data_parsed


def sliding_window(
        seq: Iterable[Any],
        size: int,
        step: int
    ) -> List[Dict[str, Any]]:
    """
    Create overlapping chunks from a sequence using a sliding window approach.

    Args:
        seq: The input sequence (string or list) to be chunked.
        size (int): The size of each chunk/window.
        step (int): The step size between consecutive windows.

    Returns:
        list: A list of dictionaries, each containing:
            - 'start': The starting position of the chunk in the original sequence
            - 'content': The chunk content

    Raises:
        ValueError: If size or step are not positive integers.

    Example:
        >>> sliding_window("hello world", size=5, step=3)
        [{'start': 0, 'content': 'hello'}, {'start': 3, 'content': 'lo wo'}]
    """
    if size <= 0 or step <= 0:
        raise ValueError("size and step must be positive")

    n = len(seq)
    result = []
    for i in range(0, n, step):
        batch = seq[i:i+size]
        result.append({'start': i, 'content': batch})
        if i + size > n:
            break

    return result


def chunk_documents(
        documents: Iterable[Dict[str, str]],
        size: int = 2000,
        step: int = 1000,
        content_field_name: str = 'content'
) -> List[Dict[str, str]]:
    """
    Split a collection of documents into smaller chunks using sliding windows.

    Takes documents and breaks their content into overlapping chunks while preserving
    all other document metadata (filename, etc.) in each chunk.

    Args:
        documents: An iterable of document dictionaries. Each document must have a content field.
        size (int, optional): The maximum size of each chunk. Defaults to 2000.
        step (int, optional): The step size between chunks. Defaults to 1000.
        content_field_name (str, optional): The name of the field containing document content.
                                          Defaults to 'content'.

    Returns:
        list: A list of chunk dictionaries. Each chunk contains:
            - All original document fields except the content field
            - 'start': Starting position of the chunk in original content
            - 'content': The chunk content

    Example:
        >>> documents = [{'content': 'long text...', 'filename': 'doc.txt'}]
        >>> chunks = chunk_documents(documents, size=100, step=50)
        >>> # Or with custom content field:
        >>> documents = [{'text': 'long text...', 'filename': 'doc.txt'}]
        >>> chunks = chunk_documents(documents, content_field_name='text')
    """
    results = []

    for doc in documents:
        doc_copy = doc.copy()
        doc_content = doc_copy.pop(content_field_name)
        chunks = sliding_window(doc_content, size=size, step=step)
        for chunk in chunks:
            chunk.update(doc_copy)
        results.extend(chunks)

    return results