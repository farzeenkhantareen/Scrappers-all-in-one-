from bs4 import BeautifulSoup

fp = "C:/Users/farze/.gemini/antigravity-ide/brain/18b2e60a-7b9a-46e7-a272-88fdb8a65814/scratch_gmaps.html"
with open(fp, "r", encoding="utf-8") as f:
    content = f.read()

soup = BeautifulSoup(content, "lxml")

print("Searching for elements with 'data-review-id'...")
els = soup.find_all(lambda tag: tag.has_attr("data-review-id"))
print(f"Total elements with data-review-id: {len(els)}")
for i, el in enumerate(els[:5]):
    print(f"Element[{i}]: tag=<{el.name}> class='{el.get('class')}'")
    parent = el.parent
    print(f"  Parent: tag=<{parent.name}> class='{parent.get('class')}'")
    gparent = parent.parent if parent else None
    if gparent:
        print(f"  Grandparent: tag=<{gparent.name}> class='{gparent.get('class')}'")
