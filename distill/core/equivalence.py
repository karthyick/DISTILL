"""
Equivalence partitioning for DISTILL.

Groups identical encoded tuples into equivalence classes.
This provides the third compression layer after schema extraction and dictionary encoding.

Mathematical basis: Set partitioning S/~ = {[x]₁, [x]₂, ...}
"""

from typing import Any, Dict, List, Tuple, Optional
from collections import defaultdict
import re


class EquivalencePartitioner:
    """
    Groups repeated encoded tuples into equivalence classes.

    Uses #N notation for equivalence references to clearly distinguish
    from dictionary codes (a-z).
    """

    def __init__(self, min_occurrences: int = 2):
        self.min_occurrences = min_occurrences
        self.equivalences: Dict[str, str] = {}  # "#0" -> "abc"
        self.reverse_equiv: Dict[str, str] = {}  # "abc" -> "#0"
        # Regex to identify strings that look like references (# followed by digits)
        self.ref_pattern = re.compile(r'^#\d+$')

    def find_equivalences(self, encoded_tuples: List[str]) -> Tuple[Dict[str, str], List[str]]:
        """
        Find repeated tuples and create equivalence references.
        """
        if not encoded_tuples:
            return {}, []

        # Count occurrences of each pattern
        counts = defaultdict(list)
        for idx, encoded in enumerate(encoded_tuples):
            counts[encoded].append(idx)

        # Find patterns that repeat enough times
        self.equivalences = {}
        self.reverse_equiv = {}
        equiv_counter = 0

        # Sort by frequency (most common first) for consistent ordering
        # Tie-break with pattern string for determinism
        sorted_patterns = sorted(
            counts.items(),
            key=lambda x: (-len(x[1]), x[0])
        )

        for pattern, indices in sorted_patterns:
            if len(indices) >= self.min_occurrences:
                ref = f"#{equiv_counter}"
                self.equivalences[ref] = pattern
                self.reverse_equiv[pattern] = ref
                equiv_counter += 1

        # Build final data with references substituted and collisions escaped
        final_data = []
        for encoded in encoded_tuples:
            if encoded in self.reverse_equiv:
                final_data.append(self.reverse_equiv[encoded])
            else:
                # Collision avoidance:
                # 1. If it looks like a ref (#N), escape it -> \#N
                # 2. If it starts with escape char (\), escape it -> \\...
                # This ensures we can unambiguously reverse the process.
                if self.ref_pattern.match(encoded):
                    final_data.append(f"\\{encoded}")
                elif encoded.startswith("\\"):
                    final_data.append(f"\\{encoded}")
                else:
                    final_data.append(encoded)

        return self.equivalences, final_data

    def expand_equivalences(self, data: List[str]) -> List[str]:
        """
        Expand equivalence references back to encoded tuples.
        """
        result = []
        for item in data:
            if not isinstance(item, str):
                # Should not happen in valid DISTILL format, but defensive
                result.append(item)
                continue
                
            if item.startswith('#'):
                # Potential reference
                if item in self.equivalences:
                    result.append(self.equivalences[item])
                else:
                    # Unknown ref - this is an error in the data or logic.
                    # We treat it as a literal to be safe, but it implies data corruption
                    # or a mismatch in equivalence map.
                    result.append(item)
            elif item.startswith('\\'):
                # Escaped literal (either \#N or \\...)
                # Remove one level of escaping
                result.append(item[1:])
            else:
                # Regular literal
                result.append(item)
        return result

    def set_equivalences(self, equivalences: Dict[str, str]) -> None:
        self.equivalences = equivalences
        self.reverse_equiv = {v: k for k, v in equivalences.items()}

    def get_compression_stats(self) -> Dict[str, Any]:
        """Return stats about equivalence compression achieved."""
        return {
            "equiv_classes": len(self.equivalences),
            "patterns": list(self.equivalences.values())
        }

    def get_stats(self) -> Dict[str, Any]:
        """Legacy alias for get_compression_stats."""
        return self.get_compression_stats()


# Convenience functions for direct use

def apply_equivalence(
    encoded_tuples: List[str],
    min_occurrences: int = 2
) -> Tuple[Dict[str, str], List[str]]:
    """
    Apply equivalence partitioning to encoded tuples.

    Convenience function for direct use without instantiating EquivalencePartitioner.

    Args:
        encoded_tuples: List of encoded tuples from dictionary encoding
        min_occurrences: Minimum times a pattern must appear to form equivalence

    Returns:
        Tuple of (equivalences, final_data) where:
        - equivalences: {"#0": "abc"} mapping refs to patterns
        - final_data: ["#0", "abd", "#0"] with refs substituted
    """
    partitioner = EquivalencePartitioner(min_occurrences)
    return partitioner.find_equivalences(encoded_tuples)


def expand_equivalences(
    data: List[str],
    equivalences: Dict[str, str]
) -> List[str]:
    """
    Expand equivalence references back to patterns.

    Args:
        data: List with #N references
        equivalences: Dictionary mapping #N refs to patterns

    Returns:
        List with references expanded
    """
    partitioner = EquivalencePartitioner()
    partitioner.set_equivalences(equivalences)
    return partitioner.expand_equivalences(data)


def get_equivalence_classes(
    encoded_tuples: List[str],
    min_occurrences: int = 2
) -> Dict[str, str]:
    """
    Get equivalence classes without transforming data.

    Args:
        encoded_tuples: List of encoded tuples
        min_occurrences: Minimum times a pattern must appear

    Returns:
        Dictionary of equivalence classes
    """
    partitioner = EquivalencePartitioner(min_occurrences)
    equivalences, _ = partitioner.find_equivalences(encoded_tuples)
    return equivalences
