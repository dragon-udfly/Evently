"""NotificationAgent - goal: tell the right person what affects them.

Rules (reactive: it listens to every broadcast INFORM)
  N1  booking_confirmed / booking_cancelled / event_cancelled -> the booking user.
  N2  hold_offered / hold_expired -> the waiting user.
  N3  hire_confirmed / hire_decided -> the requester; hire_escalated -> admins.
  N4  suspicious_scan -> admins.
Unknown topics are ignored.
"""
from .base import Agent



class NotificationAgent(Agent):
    name = "NotificationAgent"

    