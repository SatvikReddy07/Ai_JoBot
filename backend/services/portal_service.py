"""Portal classification and manual fallback. Never fetches authenticated content."""
from urllib.parse import urlsplit
import ipaddress


def validate_portal_url(url, allow_mock=False):
    try:
        parsed = urlsplit(url)
        host = parsed.hostname or ""
        if allow_mock and parsed.scheme == "http" and host in {"127.0.0.1", "localhost"}:
            return url
        if parsed.scheme != "https" or not host or parsed.username or parsed.password:
            raise ValueError("Use an HTTPS employer application URL without credentials.")
        if host in {"localhost", "metadata.google.internal"} or host.endswith((".local", ".localhost")):
            raise ValueError("Local/private application URLs are not supported.")
        try:
            if not ipaddress.ip_address(host).is_global:
                raise ValueError("Private application URLs are not supported.")
        except ValueError as exc:
            if "supported" in str(exc): raise
        if parsed.port not in (None, 443):
            raise ValueError("Use the standard HTTPS port.")
        return url
    except (TypeError, ValueError) as exc:
        raise ValueError(str(exc)) from exc


def portal_info(url):
    validate_portal_url(url)
    host = urlsplit(url).hostname.lower()
    mapping = [("greenhouse", ("greenhouse.io",)), ("lever", ("lever.co",)),
               ("workday", ("myworkdayjobs.com", "myworkdaysite.com")),
               ("linkedin", ("linkedin.com",)), ("naukri", ("naukri.com",))]
    name = next((name for name, domains in mapping if any(host == d or host.endswith("."+d) for d in domains)), "employer_portal")
    return dict(name=name, supported=True, automation_supported=False,
        features=["Open listing", "Download approved documents", "Review answers", "Record manual confirmation"],
        limitations=["Authentication, CAPTCHA and final submission are manual.",
                      "Employer identity and official destination must be verified by the user.",
                      "No authenticated scraping. Optional browser helper supports an explicit field allowlist only."])


def vacancy_key(url):
    """Normalize only tracking parameters; retain vacancy-identifying query fields."""
    from urllib.parse import parse_qsl, urlencode, urlunsplit
    p = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in {"gh_src", "source", "ref", "trackingid"}]
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), urlencode(sorted(query)), ""))
