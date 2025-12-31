"""Quick test of a single question to verify the fix."""

from src.main import answer

print("=" * 80)
print("TESTING SINGLE QUESTION")
print("=" * 80)

question = "Comment éviter les frais de roaming hors Europe?"
print(f"\nQuestion: {question}\n")

print("Calling agent...")
response = answer(question)

print("\n" + "=" * 80)
print("RESPONSE:")
print("=" * 80)
print(response)
print("=" * 80)

# Check for problems
print("\n" + "=" * 80)
print("DIAGNOSTICS:")
print("=" * 80)

problems = []

if "(Source:" in response:
    problems.append("❌ Contains '(Source:...)' metadata")

if "FAQ_" in response:
    problems.append("❌ Contains PDF filename")

if "TelecomPlus" in response:
    problems.append("❌ Contains 'TelecomPlus' header")

if "Page:" in response or "page:" in response:
    problems.append("❌ Contains 'Page:' reference")

if "©" in response:
    problems.append("❌ Contains copyright symbol")

if "|" in response:
    problems.append("❌ Contains table formatting")

if "Informations FAQ:" in response:
    problems.append("❌ Contains 'Informations FAQ:' prefix")

if len(response) < 50:
    problems.append("⚠️  Response is very short (< 50 chars)")

if len(response) > 500:
    problems.append("⚠️  Response is very long (> 500 chars)")

# Check for good signs
good_signs = []

if any(word in response.lower() for word in ["recommandons", "pouvez", "désactiver", "wifi"]):
    good_signs.append("✅ Contains relevant keywords")

if "." in response:
    good_signs.append("✅ Has proper sentences")

if response[0].isupper():
    good_signs.append("✅ Starts with capital letter")

# Print results
if problems:
    print("\nProblems found:")
    for p in problems:
        print(f"  {p}")
else:
    print("\n✅ No problems detected!")

if good_signs:
    print("\nGood signs:")
    for g in good_signs:
        print(f"  {g}")

# Final verdict
print("\n" + "=" * 80)
if not problems and len(good_signs) >= 2:
    print("✅ ✅ ✅ SUCCESS! Response looks good!")
elif len(problems) <= 1 and good_signs:
    print("⚠️  MOSTLY OK - Minor issues")
else:
    print("❌ FAILED - Major issues remain")
print("=" * 80)