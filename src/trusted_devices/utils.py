from httpx import Client, HTTPError


def get_client_ip(request) -> str:
    """
    Returns the client's real IP address, checking 'X-Forwarded-For' first,
    then falling back to 'REMOTE_ADDR'.

    Args:
        request: Django HTTP request object.

    Returns:
        str: Client IP address as a string.
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        # X-Forwarded-For may contain multiple IPs. We take the first one.
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def get_location_data(ip: str) -> dict:
    """
    Fetches approximate location data (country, region, city) from IP address
    using the ipapi.co external API.

    Args:
        ip (str): IP address to lookup.

    Returns:
        dict: Dictionary with keys 'country', 'region', and 'city'.
              Returns empty dict on failure.
    """
    try:
        with Client(timeout=5.0) as client:
            response = client.get(f"https://ipapi.co/{ip}/json/")
            response.raise_for_status()
            data = response.json()
            return {
                "country": data.get("country_name"),
                "region": data.get("region"),
                "city": data.get("city"),
            }
    except (HTTPError, ValueError, KeyError):
        return {}


def format_duration(minutes: int) -> str:
    """
    Converts a duration in minutes into a human-readable string format such as:
    "1 week, 2 days, 3 hours, 15 minutes".

    Args:
        minutes (int): Total duration in minutes.

    Returns:
        str: Human-readable formatted string.
    """
    parts = []

    weeks, minutes = divmod(minutes, 60 * 24 * 7)
    if weeks:
        parts.append(f"{weeks} week{'s' if weeks != 1 else ''}")

    days, minutes = divmod(minutes, 60 * 24)
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")

    hours, minutes = divmod(minutes, 60)
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")

    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

    return ", ".join(parts) if parts else "0 minutes"
