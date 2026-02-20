def to_json_safe(obj):
    """
    Recursively convert objects into JSON-serializable structures.
    """

    # primitives
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj

    # list / tuple
    if isinstance(obj, (list, tuple)):
        return [to_json_safe(x) for x in obj]

    # dict
    if isinstance(obj, dict):
        return {k: to_json_safe(v) for k, v in obj.items()}

    # object with __dict__ (Whisper Word / Segment)
    if hasattr(obj, "__dict__"):
        return {
            k: to_json_safe(v)
            for k, v in vars(obj).items()
            if not k.startswith("_")
        }

    # fallback
    return str(obj)