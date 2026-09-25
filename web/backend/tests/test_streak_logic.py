import pytest
from datetime import datetime, timezone, timedelta, date
from zoneinfo import ZoneInfo
from main import compute_consecutive_streak, to_user_date


class TestConsecutiveStreakLogic:
    """Test suite verifying consecutive calendar day streak calculations and edge cases."""

    def test_new_user_no_activity(self):
        """A user with 0 activity dates should have a 0 streak."""
        today = date(2026, 9, 24)
        streak_days, streak_active_today = compute_consecutive_streak(set(), today)
        assert streak_days == 0
        assert streak_active_today is False

    def test_single_day_active_today(self):
        """User completed an activity today: streak is 1, active today is True."""
        today = date(2026, 9, 24)
        activity_dates = {today}
        streak_days, streak_active_today = compute_consecutive_streak(activity_dates, today)
        assert streak_days == 1
        assert streak_active_today is True

    def test_morning_after_activity_yesterday(self):
        """
        User studied yesterday. Today is morning, no study done yet today.
        Streak from yesterday (1 day) is preserved, active today is False (prompt to study).
        """
        yesterday = date(2026, 9, 23)
        today = date(2026, 9, 24)
        activity_dates = {yesterday}
        streak_days, streak_active_today = compute_consecutive_streak(activity_dates, today)
        assert streak_days == 1
        assert streak_active_today is False

    def test_consecutive_days_active_today(self):
        """User studied on Day 1, Day 2, and Day 3 (today): streak is 3, active today is True."""
        d1 = date(2026, 9, 22)
        d2 = date(2026, 9, 23)
        d3 = date(2026, 9, 24)
        activity_dates = {d1, d2, d3}
        streak_days, streak_active_today = compute_consecutive_streak(activity_dates, d3)
        assert streak_days == 3
        assert streak_active_today is True

    def test_consecutive_days_morning_hold(self):
        """
        User studied on Day 1, Day 2, Day 3. Now morning of Day 4.
        Streak of 3 is preserved from yesterday until midnight.
        """
        d1 = date(2026, 9, 22)
        d2 = date(2026, 9, 23)
        d3 = date(2026, 9, 24)
        d4 = date(2026, 9, 25)
        activity_dates = {d1, d2, d3}
        streak_days, streak_active_today = compute_consecutive_streak(activity_dates, d4)
        assert streak_days == 3
        assert streak_active_today is False

    def test_missed_day_before_studying(self):
        """
        User studied on Day 1 and Day 2.
        Day 3 was completely missed.
        Morning of Day 4 arrives (no study yet today).
        Streak is broken (0 days).
        """
        d1 = date(2026, 9, 20)
        d2 = date(2026, 9, 21)
        # d3 (2026-09-22) MISSED!
        d4 = date(2026, 9, 23)
        activity_dates = {d1, d2}
        streak_days, streak_active_today = compute_consecutive_streak(activity_dates, d4)
        assert streak_days == 0
        assert streak_active_today is False

    def test_missed_day_resets_to_one_when_resumed(self):
        """
        User studied on Day 1 and Day 2.
        Day 3 was missed.
        User resumes and studies on Day 4: streak correctly resets to 1!
        """
        d1 = date(2026, 9, 20)
        d2 = date(2026, 9, 21)
        # d3 (2026-09-22) MISSED!
        d4 = date(2026, 9, 23)
        activity_dates = {d1, d2, d4}  # Resumed on d4
        streak_days, streak_active_today = compute_consecutive_streak(activity_dates, d4)
        assert streak_days == 1
        assert streak_active_today is True

    def test_multiple_weeks_simulation(self):
        """
        Simulate a realistic 10-day timeline:
        - Days 1 to 4: daily activity (streak grows 1 -> 4)
        - Day 5: missed
        - Day 6: active (resets to 1)
        - Day 7: active (grows to 2)
        - Day 8: active (grows to 3)
        - Day 9: morning (holds at 3, active_today=False)
        """
        base = date(2026, 10, 1)
        dates = [base + timedelta(days=i) for i in range(10)]

        history = set()

        # Day 0 (Oct 1)
        history.add(dates[0])
        s, a = compute_consecutive_streak(history, dates[0])
        assert (s, a) == (1, True)

        # Day 1 (Oct 2)
        history.add(dates[1])
        s, a = compute_consecutive_streak(history, dates[1])
        assert (s, a) == (2, True)

        # Day 2 (Oct 3)
        history.add(dates[2])
        s, a = compute_consecutive_streak(history, dates[2])
        assert (s, a) == (3, True)

        # Day 3 (Oct 4)
        history.add(dates[3])
        s, a = compute_consecutive_streak(history, dates[3])
        assert (s, a) == (4, True)

        # Day 4 (Oct 5) - MISSED entirely!
        # Day 5 (Oct 6) morning - before studying
        s, a = compute_consecutive_streak(history, dates[5])
        assert (s, a) == (0, False)

        # Day 5 (Oct 6) afternoon - user studies! Streak resets to 1
        history.add(dates[5])
        s, a = compute_consecutive_streak(history, dates[5])
        assert (s, a) == (1, True)

        # Day 6 (Oct 7) - user studies! Streak grows to 2
        history.add(dates[6])
        s, a = compute_consecutive_streak(history, dates[6])
        assert (s, a) == (2, True)

        # Day 7 (Oct 8) - user studies! Streak grows to 3
        history.add(dates[7])
        s, a = compute_consecutive_streak(history, dates[7])
        assert (s, a) == (3, True)

        # Day 8 (Oct 9) morning - user hasn't studied yet today
        s, a = compute_consecutive_streak(history, dates[8])
        assert (s, a) == (3, False)


class TestToUserDateConversion:
    """Verify timezone and date string parsing accuracy."""

    def test_iso_utc_string_conversion(self):
        user_tz = ZoneInfo("Asia/Karachi")  # UTC+5
        # 2026-09-23 20:00 UTC is 2026-09-24 01:00 in Karachi
        iso_str = "2026-09-23T20:00:00Z"
        d = to_user_date(iso_str, user_tz)
        assert d == date(2026, 9, 24)

    def test_direct_date_string_not_shifted(self):
        """A plain YYYY-MM-DD date string must not shift backwards in US timezones."""
        ny_tz = ZoneInfo("America/New_York")
        date_str = "2026-09-24"
        d = to_user_date(date_str, ny_tz)
        assert d == date(2026, 9, 24)

    def test_python_datetime_conversion(self):
        user_tz = timezone.utc
        now = datetime(2026, 9, 24, 12, 0, 0, tzinfo=timezone.utc)
        d = to_user_date(now, user_tz)
        assert d == date(2026, 9, 24)

    def test_python_date_direct(self):
        user_tz = timezone.utc
        d_orig = date(2026, 9, 24)
        d = to_user_date(d_orig, user_tz)
        assert d == d_orig
