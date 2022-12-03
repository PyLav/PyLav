def is_url(uri: str) -> bool:
    return f"{uri}".startswith(("https://", "http://", "s3://", "s3a://", "s3n://"))
