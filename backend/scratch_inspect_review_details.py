import sys
sys.stdout.reconfigure(encoding='utf-8')
from bs4 import BeautifulSoup

fp = "C:/Users/farze/.gemini/antigravity-ide/brain/18b2e60a-7b9a-46e7-a272-88fdb8a65814/scratch_gmaps.html"
with open(fp, "r", encoding="utf-8") as f:
    content = f.read()

soup = BeautifulSoup(content, "lxml")

card = soup.find("div", class_="jftiEf")
if card:
    print("Found review card!")
    # Find reviewer name elements
    print("Reviewer Name tags:")
    for tag in card.find_all(class_=True):
        classes = tag.get("class")
        # Check if text is non-empty
        text = tag.text.strip()
        if text and len(text) < 100:
            print(f"  <{tag.name}> class={classes} text='{text}'")
else:
    print("Review card not found!")
