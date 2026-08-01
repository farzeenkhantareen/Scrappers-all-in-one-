from bs4 import BeautifulSoup

fp = "C:/Users/farze/.gemini/antigravity-ide/brain/18b2e60a-7b9a-46e7-a272-88fdb8a65814/scratch_gmaps.html"
with open(fp, "r", encoding="utf-8") as f:
    content = f.read()

soup = BeautifulSoup(content, "lxml")
print(f"Title: {soup.title.text if soup.title else None}")
print(f"All H1 tags count: {len(soup.find_all('h1'))}")
for i, h1 in enumerate(soup.find_all('h1')):
    print(f"H1[{i}]: text='{h1.text.strip()}' class='{h1.get('class')}'")

# Search for the business name
if "Ensys" in content:
    print("Found 'Ensys' in content!")
else:
    print("Did NOT find 'Ensys' in content!")

# Print buttons
buttons = soup.find_all("button")
print(f"Total buttons: {len(buttons)}")
for btn in buttons[:10]:
    print(f"Button: text='{btn.text.strip()}' class='{btn.get('class')}' aria-label='{btn.get('aria-label')}'")
