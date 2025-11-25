"""
File I/O support for DISTILL.

Provides functions for reading and writing DISTILL files,
with support for JSON, DISTILL format, and streaming.
"""

import json
import gzip
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union

from .compress import compress
from .decompress import decompress
from .exceptions import DistillError, ValidationError


class DistillIO:
    """
    File I/O handler for DISTILL format.

    Supports:
        - JSON input/output
        - DISTILL format (.distill extension)
        - Gzip compression (.gz extension)
        - Streaming for large files
    """

    DISTILL_EXTENSION = ".distill"
    GZIP_EXTENSION = ".gz"

    def __init__(self, encoding: str = "utf-8"):
        """
        Initialize the I/O handler.

        Args:
            encoding: Text encoding (default: utf-8)
        """
        self.encoding = encoding

    def read_json(self, path: Union[str, Path]) -> Any:
        """
        Read and parse a JSON file.

        Args:
            path: Path to JSON file

        Returns:
            Parsed JSON data

        Raises:
            FileNotFoundError: If file doesn't exist
            ValidationError: If JSON is invalid
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        try:
            opener = gzip.open if path.suffix == self.GZIP_EXTENSION else open
            with opener(path, "rt", encoding=self.encoding) as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON in {path}: {e}")

    def write_json(
        self,
        data: Any,
        path: Union[str, Path],
        indent: Optional[int] = 2,
        compress_gzip: bool = False
    ) -> Path:
        """
        Write data to a JSON file.

        Args:
            data: Data to write
            path: Output path
            indent: JSON indentation (None for compact)
            compress_gzip: Whether to gzip the output

        Returns:
            Path to written file
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if compress_gzip and not path.suffix == self.GZIP_EXTENSION:
            path = path.with_suffix(path.suffix + self.GZIP_EXTENSION)

        opener = gzip.open if compress_gzip or path.suffix == self.GZIP_EXTENSION else open
        with opener(path, "wt", encoding=self.encoding) as f:
            json.dump(data, f, indent=indent)

        return path

    def read_distill(self, path: Union[str, Path]) -> str:
        """
        Read a DISTILL compressed file.

        Args:
            path: Path to DISTILL file

        Returns:
            Compressed string content

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        opener = gzip.open if path.suffix == self.GZIP_EXTENSION else open
        with opener(path, "rt", encoding=self.encoding) as f:
            return f.read()

    def write_distill(
        self,
        compressed: str,
        path: Union[str, Path],
        compress_gzip: bool = False
    ) -> Path:
        """
        Write compressed DISTILL content to file.

        Args:
            compressed: Compressed DISTILL string
            path: Output path
            compress_gzip: Whether to gzip the output

        Returns:
            Path to written file
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if compress_gzip and not path.suffix == self.GZIP_EXTENSION:
            path = path.with_suffix(path.suffix + self.GZIP_EXTENSION)

        opener = gzip.open if compress_gzip or path.suffix == self.GZIP_EXTENSION else open
        with opener(path, "wt", encoding=self.encoding) as f:
            f.write(compressed)

        return path

    def compress_file(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        level: str = "auto",
        gzip_output: bool = False
    ) -> Dict[str, Any]:
        """
        Compress a JSON file to DISTILL format.

        Args:
            input_path: Path to input JSON file
            output_path: Path to output file (default: input_path.distill)
            level: Compression level
            gzip_output: Whether to gzip the output

        Returns:
            Result dict with meta and output_path
        """
        input_path = Path(input_path)

        if output_path is None:
            output_path = input_path.with_suffix(self.DISTILL_EXTENSION)
        output_path = Path(output_path)

        # Read and compress
        data = self.read_json(input_path)
        result = compress(data, level=level)

        # Write output
        written_path = self.write_distill(
            result["compressed"],
            output_path,
            compress_gzip=gzip_output
        )

        result["output_path"] = str(written_path)
        result["input_path"] = str(input_path)

        return result

    def decompress_file(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        pretty: bool = True,
        gzip_output: bool = False
    ) -> Dict[str, Any]:
        """
        Decompress a DISTILL file to JSON.

        Args:
            input_path: Path to input DISTILL file
            output_path: Path to output file (default: input_path.json)
            pretty: Whether to pretty-print JSON
            gzip_output: Whether to gzip the output

        Returns:
            Result dict with data and output_path
        """
        input_path = Path(input_path)

        if output_path is None:
            # Remove .distill extension and add .json
            stem = input_path.stem
            if stem.endswith(".distill"):
                stem = stem[:-8]
            output_path = input_path.parent / f"{stem}.json"
        output_path = Path(output_path)

        # Read and decompress
        compressed = self.read_distill(input_path)
        data = decompress(compressed)

        # Write output
        written_path = self.write_json(
            data,
            output_path,
            indent=2 if pretty else None,
            compress_gzip=gzip_output
        )

        return {
            "data": data,
            "output_path": str(written_path),
            "input_path": str(input_path)
        }


def stream_json_array(path: Union[str, Path], chunk_size: int = 100) -> Iterator[List[Dict]]:
    """
    Stream a large JSON array file in chunks.

    Useful for processing very large JSON arrays without loading
    the entire file into memory.

    Args:
        path: Path to JSON file containing an array
        chunk_size: Number of items per chunk

    Yields:
        Lists of items from the JSON array

    Note:
        This is a simple implementation that still loads
        the full file. For truly large files, consider
        using ijson or similar streaming JSON parsers.
    """
    path = Path(path)
    io_handler = DistillIO()
    data = io_handler.read_json(path)

    if not isinstance(data, list):
        raise ValidationError("stream_json_array requires a JSON array file")

    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]


def batch_compress(
    input_dir: Union[str, Path],
    output_dir: Optional[Union[str, Path]] = None,
    pattern: str = "*.json",
    level: str = "auto",
    recursive: bool = False
) -> List[Dict[str, Any]]:
    """
    Compress multiple JSON files in a directory.

    Args:
        input_dir: Input directory
        output_dir: Output directory (default: same as input)
        pattern: Glob pattern for files
        level: Compression level
        recursive: Whether to search recursively

    Returns:
        List of compression results
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir) if output_dir else input_dir

    io_handler = DistillIO()
    results = []

    glob_method = input_dir.rglob if recursive else input_dir.glob

    for json_file in glob_method(pattern):
        # Determine output path
        relative = json_file.relative_to(input_dir)
        out_path = output_dir / relative.with_suffix(DistillIO.DISTILL_EXTENSION)

        try:
            result = io_handler.compress_file(json_file, out_path, level=level)
            result["status"] = "success"
        except Exception as e:
            result = {
                "input_path": str(json_file),
                "status": "error",
                "error": str(e)
            }

        results.append(result)

    return results


# Convenience functions
def compress_file(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    level: str = "auto"
) -> Dict[str, Any]:
    """
    Compress a JSON file to DISTILL format.

    Args:
        input_path: Path to input JSON file
        output_path: Path to output file
        level: Compression level

    Returns:
        Result dict with meta and output_path
    """
    return DistillIO().compress_file(input_path, output_path, level)


def decompress_file(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None
) -> Dict[str, Any]:
    """
    Decompress a DISTILL file to JSON.

    Args:
        input_path: Path to input DISTILL file
        output_path: Path to output file

    Returns:
        Result dict with data and output_path
    """
    return DistillIO().decompress_file(input_path, output_path)
