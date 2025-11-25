
from distill.core.schema import MISSING, reconstruct_objects
from distill.core.huffman import flatten_nested_value, unflatten_value, DictionaryEncoder

print(f"MISSING: {MISSING!r}")
print(f"Type of MISSING: {type(MISSING)}")

flat = flatten_nested_value(MISSING)
print(f"Flattened MISSING: {flat!r}")

unflat = unflatten_value(flat)
print(f"Unflattened: {unflat!r}")
print(f"Is MISSING? {unflat is MISSING}")

# Test reconstruct
schema = ["a"]
tuples = [[unflat]]
objs = reconstruct_objects(schema, tuples)
print(f"Reconstructed: {objs}")
