import pytest
from backend.connectors.base import clean_html, parse_location, parse_employment_type

def test_clean_html():
    raw = "<p>Join our team as <strong>Global HSE Manager</strong>.<br/>Key points:<ul><li>Lead safety</li><li>Ensure compliance</li></ul></p>"
    cleaned = clean_html(raw)
    assert "Global HSE Manager" in cleaned
    assert "Lead safety" in cleaned
    assert "<p>" not in cleaned
    assert "<strong>" not in cleaned

def test_parse_location_target_countries():
    # India
    city, country = parse_location("Hyderabad, Telangana, India")
    assert country == "India"
    assert city == "Hyderabad"

    # Singapore
    city, country = parse_location("Singapore Central, Singapore")
    assert country == "Singapore"

    # Germany
    city, country = parse_location("Berlin, Germany")
    assert country == "Germany"
    assert city == "Berlin"

    # Netherlands
    city, country = parse_location("Amsterdam, Netherlands")
    assert country == "Netherlands"
    assert city == "Amsterdam"

    # Ireland
    city, country = parse_location("Dublin, Ireland")
    assert country == "Ireland"
    assert city == "Dublin"

    # Australia
    city, country = parse_location("Sydney, NSW, Australia")
    assert country == "Australia"
    assert city == "Sydney"

    # Unknown
    city, country = parse_location("")
    assert country == "Unknown"

def test_parse_employment_type():
    emp1, is_p1 = parse_employment_type("This is a permanent full-time position.")
    assert emp1 == "Permanent Full-time"
    assert is_p1 is True

    emp2, is_p2 = parse_employment_type("6 month temporary contract assignment")
    assert emp2 == "Contract / Temporary"
    assert is_p2 is False

    emp3, is_p3 = parse_employment_type("We offer competitive salary and perks.")
    assert emp3 == "Unknown"
    assert is_p3 is False
