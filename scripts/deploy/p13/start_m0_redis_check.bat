@echo off
REM P13 Redis check template. This does not start or install Redis.
redis-cli ping
if errorlevel 1 (
  echo Redis unavailable. Start Redis manually on M0.
) else (
  echo Redis available.
)
