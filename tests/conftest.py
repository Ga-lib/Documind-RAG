"""Test environment defaults must be set before application imports."""
import os

os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
