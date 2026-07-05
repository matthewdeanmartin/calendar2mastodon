"""Metadata for calendar2mastodon."""

__all__ = [
    "__credits__",
    "__dependencies__",
    "__description__",
    "__keywords__",
    "__license__",
    "__readme__",
    "__requires_python__",
    "__status__",
    "__title__",
    "__version__",
]

__title__ = "calendar2mastodon"
__version__ = "0.1.0"
__description__ = "A Python tool to post calendar events to Mastodon"
__readme__ = "README.md"
__credits__ = [{'name': 'Matthew Martin', 'email': 'matthewdeanmartin@gmail.com'}]
__keywords__ = ['calendar2mastodon']
__license__ = "MIT"
__requires_python__ = ">=3.10"
__status__ = "3 - Alpha"
__dependencies__ = [
    "httpx>=0.27.0",
    "icalendar>=6.0.0",
    "Mastodon.py>=1.8.0",
    "tomli>=2.0.0; python_version < '3.11'",
    "tzdata>=2024.1",
]