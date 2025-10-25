"""
Rate limiter for chat endpoint
Implements per-user rate limiting with rolling time windows
"""
from datetime import datetime, timedelta
from fastapi import HTTPException
from typing import Callable
import sqlite3


class RateLimiter:
    """Per-user rate limiter with rolling time windows"""

    def __init__(self, db_factory: Callable, limit: int, window_hours: int):
        """
        Initialize rate limiter

        Args:
            db_factory: Function that returns a database connection context manager
            limit: Maximum number of requests allowed per window
            window_hours: Size of the rolling time window in hours
        """
        self.db_factory = db_factory
        self.limit = limit
        self.window = timedelta(hours=window_hours)

    def check_rate_limit(self, email: str) -> None:
        """
        Check if user has exceeded rate limit

        Args:
            email: User's email address

        Raises:
            HTTPException: 429 Too Many Requests if rate limit exceeded
        """
        with self.db_factory() as conn:
            cursor = conn.cursor()

            # Get current rate limit record
            cursor.execute(
                "SELECT request_count, window_start FROM chat_rate_limits WHERE email = ?",
                (email,)
            )
            result = cursor.fetchone()

            now = datetime.utcnow()

            if result is None:
                # First request from this user - create record
                cursor.execute(
                    "INSERT INTO chat_rate_limits (email, request_count, window_start) VALUES (?, 1, ?)",
                    (email, now)
                )
                conn.commit()
                return

            request_count = result['request_count']
            window_start = datetime.fromisoformat(result['window_start'])

            # Check if we're still in the same window
            if now - window_start < self.window:
                # Still in current window
                if request_count >= self.limit:
                    # Rate limit exceeded
                    time_remaining = self.window - (now - window_start)
                    minutes_remaining = int(time_remaining.total_seconds() / 60)
                    raise HTTPException(
                        status_code=429,
                        detail=f"Rate limit exceeded. Try again in {minutes_remaining} minutes. (Limit: {self.limit} requests per {self.window.total_seconds() / 3600:.0f} hour(s))"
                    )

                # Increment counter
                cursor.execute(
                    "UPDATE chat_rate_limits SET request_count = request_count + 1 WHERE email = ?",
                    (email,)
                )
            else:
                # Window expired - start new window
                cursor.execute(
                    "UPDATE chat_rate_limits SET request_count = 1, window_start = ? WHERE email = ?",
                    (now, email)
                )

            conn.commit()

    def get_remaining_requests(self, email: str) -> dict:
        """
        Get rate limit status for a user

        Args:
            email: User's email address

        Returns:
            Dictionary with limit, remaining, and reset_at fields
        """
        with self.db_factory() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT request_count, window_start FROM chat_rate_limits WHERE email = ?",
                (email,)
            )
            result = cursor.fetchone()

            if result is None:
                return {
                    "limit": self.limit,
                    "remaining": self.limit,
                    "reset_at": None
                }

            request_count = result['request_count']
            window_start = datetime.fromisoformat(result['window_start'])
            now = datetime.utcnow()

            # Check if window expired
            if now - window_start >= self.window:
                return {
                    "limit": self.limit,
                    "remaining": self.limit,
                    "reset_at": None
                }

            remaining = max(0, self.limit - request_count)
            reset_at = window_start + self.window

            return {
                "limit": self.limit,
                "remaining": remaining,
                "reset_at": reset_at.isoformat() + "Z"
            }
