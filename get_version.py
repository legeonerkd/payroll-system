import re

with open("payroll.py", encoding="utf-8") as f:
    data = f.read()

match = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', data)
if not match:
    raise SystemExit("Version not found")

print(match.group(1))
