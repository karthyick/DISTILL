"""
Command-line interface for DISTILL.

Usage:
    distill compress input.json -o output.json
    distill decompress input.json -o output.json
    distill analyze input.json
    distill verify input.json
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from .compress import compress, analyze
from .decompress import decompress
from .config import configure, get_config, DistillConfig
from .core.tokenizer import count_tokens
from .exceptions import DistillError, CompressionError, DecompressionError


def read_json_file(path: str) -> Any:
    """Read and parse a JSON file."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def read_file(path: str) -> str:
    """Read a file as string."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def write_file(path: str, content: str) -> None:
    """Write content to a file."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


def cmd_compress(args: argparse.Namespace) -> int:
    """Handle compress command."""
    try:
        # Read input
        data = read_json_file(args.input)

        # Compress
        start_time = time.time()
        result = compress(data)
        elapsed = time.time() - start_time

        # Output
        if args.output:
            write_file(args.output, result["compressed"])
            if not args.quiet:
                print(f"Compressed to: {args.output}")
        else:
            print(result["compressed"])

        # Show stats
        if not args.quiet:
            meta = result["meta"]
            print(f"\n--- Compression Statistics ---")
            print(f"Method: {meta.get('method', 'N/A')}")
            print(f"Original tokens: {meta.get('original_tokens', 'N/A')}")
            print(f"Compressed tokens: {meta.get('compressed_tokens', 'N/A')}")
            print(f"Reduction: {meta.get('reduction_percent', 0):.1f}%")
            print(f"Schema fields: {meta.get('schema_fields', 0)}")
            print(f"Dictionary codes: {meta.get('dict_codes', 0)}")
            print(f"Equivalence classes: {meta.get('equiv_classes', 0)}")
            print(f"Time: {elapsed:.3f}s")
            if meta.get('fallback'):
                print(f"Note: Fallback to original (compression would increase size)")

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON - {e}", file=sys.stderr)
        return 1
    except DistillError as e:
        print(f"Error: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_decompress(args: argparse.Namespace) -> int:
    """Handle decompress command."""
    try:
        # Read input
        compressed = read_file(args.input)

        # Decompress
        start_time = time.time()
        result = decompress(compressed)
        elapsed = time.time() - start_time

        # Format output
        output_str = json.dumps(result, indent=2 if args.pretty else None)

        # Output
        if args.output:
            write_file(args.output, output_str)
            if not args.quiet:
                print(f"Decompressed to: {args.output}")
        else:
            print(output_str)

        # Show stats
        if not args.quiet and args.output:
            print(f"\n--- Decompression Statistics ---")
            print(f"Time: {elapsed:.3f}s")

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except DecompressionError as e:
        print(f"Error: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_analyze(args: argparse.Namespace) -> int:
    """Handle analyze command - shows compression analysis without compressing."""
    try:
        # Read input
        data = read_json_file(args.input)

        print(f"Analyzing: {args.input}\n")

        # Get analysis
        analysis = analyze(data)

        print(f"Original tokens: {analysis.get('original_tokens', 'N/A')}")
        print(f"Compressible: {analysis.get('compressible', False)}")

        if analysis.get('compressible'):
            print(f"\n--- Structure Analysis ---")
            print(f"Schema fields: {analysis.get('schema_fields', 0)}")
            print(f"Total tuples: {analysis.get('total_tuples', 0)}")
            print(f"Unique values: {analysis.get('unique_values', 0)}")
            print(f"Repeated tuples: {analysis.get('repeated_tuples', 0)}")
            print(f"Data key: {analysis.get('data_key', 'N/A')}")
            print(f"\nEstimated reduction: ~{analysis.get('estimated_reduction', 0)}%")

            # Actually compress to get real numbers
            print(f"\n--- Actual Compression ---")
            result = compress(data)
            meta = result["meta"]
            print(f"Method: {meta.get('method', 'N/A')}")
            print(f"Compressed tokens: {meta.get('compressed_tokens', 'N/A')}")
            print(f"Actual reduction: {meta.get('reduction_percent', 0):.1f}%")
            if meta.get('fallback'):
                print(f"Note: {meta.get('reason', 'fallback to original')}")
        else:
            print(f"Reason: {analysis.get('reason', 'unknown')}")

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON - {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_verify(args: argparse.Namespace) -> int:
    """Handle verify command - compress then decompress and check equality."""
    try:
        print(f"Verifying: {args.input}")
        
        # Read input
        data = read_json_file(args.input)
        
        # Compress
        print("Compressing...", end=" ", flush=True)
        start = time.time()
        compressed_result = compress(data)
        compress_time = time.time() - start
        print(f"Done ({compress_time:.3f}s)")
        
        # Decompress
        print("Decompressing...", end=" ", flush=True)
        start = time.time()
        restored = decompress(compressed_result["compressed"])
        decompress_time = time.time() - start
        print(f"Done ({decompress_time:.3f}s)")
        
        # Compare
        print("Comparing...", end=" ", flush=True)
        
        # Convert to JSON strings for comparison to handle potential tuple/list differences
        # or just compare directly
        if data == restored:
            print("✅ PASS")
            print("\nVerification Successful: Data matches exactly.")
            print(f"Reduction: {compressed_result['meta']['reduction_percent']:.1f}%")
            return 0
        else:
            print("❌ FAIL")
            print("\nVerification Failed: Data mismatch!")
            return 1
            
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1


def cmd_config(args: argparse.Namespace) -> int:
    """Handle config command - show or set configuration."""
    try:
        config = get_config()

        if args.show:
            print("--- Current Configuration ---")
            for key, value in config.to_dict().items():
                print(f"{key}: {value}")
            return 0

        if args.set:
            for setting in args.set:
                if '=' not in setting:
                    print(f"Error: Invalid format '{setting}'. Use 'key=value'", file=sys.stderr)
                    return 1

                key, value = setting.split('=', 1)

                # Type conversion
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                elif value.isdigit():
                    value = int(value)
                elif '.' in value:
                    try:
                        value = float(value)
                    except ValueError:
                        pass

                try:
                    configure(**{key: value})
                    print(f"Set {key} = {value}")
                except ValueError as e:
                    print(f"Error: {e}", file=sys.stderr)
                    return 1

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="distill",
        description="DISTILL - Data Intelligent Structure Token-efficient Interchange for LLMs",
        epilog="For more information, visit: https://github.com/your-repo/distill"
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version="%(prog)s 0.2.0"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Compress command
    compress_parser = subparsers.add_parser(
        "compress",
        help="Compress JSON to DISTILL format"
    )
    compress_parser.add_argument(
        "input",
        help="Input JSON file"
    )
    compress_parser.add_argument(
        "-o", "--output",
        help="Output file (default: stdout)"
    )
    compress_parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress statistics output"
    )
    compress_parser.set_defaults(func=cmd_compress)

    # Decompress command
    decompress_parser = subparsers.add_parser(
        "decompress",
        help="Decompress DISTILL format to JSON"
    )
    decompress_parser.add_argument(
        "input",
        help="Input DISTILL file"
    )
    decompress_parser.add_argument(
        "-o", "--output",
        help="Output JSON file (default: stdout)"
    )
    decompress_parser.add_argument(
        "-p", "--pretty",
        action="store_true",
        help="Pretty-print JSON output"
    )
    decompress_parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress statistics output"
    )
    decompress_parser.set_defaults(func=cmd_decompress)

    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze compression potential of JSON file"
    )
    analyze_parser.add_argument(
        "input",
        help="Input JSON file"
    )
    analyze_parser.set_defaults(func=cmd_analyze)
    
    # Verify command
    verify_parser = subparsers.add_parser(
        "verify",
        help="Verify compression/decompression roundtrip"
    )
    verify_parser.add_argument(
        "input",
        help="Input JSON file"
    )
    verify_parser.set_defaults(func=cmd_verify)

    # Config command
    config_parser = subparsers.add_parser(
        "config",
        help="View or modify configuration"
    )
    config_parser.add_argument(
        "--show",
        action="store_true",
        help="Show current configuration"
    )
    config_parser.add_argument(
        "--set",
        nargs="+",
        metavar="KEY=VALUE",
        help="Set configuration values"
    )
    config_parser.set_defaults(func=cmd_config)

    return parser


def main() -> int:
    """Main entry point for CLI."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
