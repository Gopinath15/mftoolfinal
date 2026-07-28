from mftool import Mftool

mf = Mftool()

print("--- 1. Testing Scheme Code Validation ---")
test_code = "120503"
is_valid = mf.is_valid_code(test_code)
print(f"Is '{test_code}' a valid scheme code? {is_valid}")

print("\n--- 2. Fetching Historical NAVs ---")
# Corrected method name for version 3.3
historical_data = mf.get_scheme_historical_nav(test_code)
print(list(historical_data.items())[:3] if isinstance(historical_data, dict) else historical_data.head(3))
# Print scheme metadata
print("Fund House:", historical_data.get('fund_house'))
print("Scheme Category:", historical_data.get('scheme_category'))

# Print the first 3 historical NAV entries from the 'data' list
nav_entries = historical_data.get('data', [])
print("First 3 NAV records:", nav_entries[:3])