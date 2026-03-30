# Shadow AI v2.75

Release type: Linux update

## Highlights

- stronger SILS local runtime behavior
- hardened template-backed intent handling
- safer local command routing and review
- improved file handling and honesty fallback
- cleaned warning behavior
- green full Python test suite

## Linux Install Direction

- Debian and Ubuntu users can keep using `.deb` release assets
- broader Linux support now leans on source install through `install.sh`
- `run.sh` now bootstraps install on first run if needed

## Validation

- Python test suite: `65/65`
- hardened SILS benchmark: `32/32`

## Notes

This release keeps Shadow local-first and memory-first. Shadow remembers through its memory systems and structured retrieval. TinyLM behavior still improves through retraining instead of hidden live weight updates.
