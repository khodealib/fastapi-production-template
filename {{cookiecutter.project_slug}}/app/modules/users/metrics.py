"""Business metrics for the users module."""

from prometheus_client import Counter

user_registrations_total = Counter(
    "user_registrations_total",
    "Total number of user registrations.",
)

user_authentication_attempts_total = Counter(
    "user_authentication_attempts_total",
    "Total number of login attempts.",
    ["outcome"],
)

token_refresh_total = Counter(
    "token_refresh_total",
    "Total number of token refresh operations.",
    ["outcome"],
)
