import json
import random
import os

AUTHORS = ["John Smith", "Mary Jones", "Alice Walker", "David Hume", "Immanuel Kant"]
SUBJECTS = ["History", "Art", "Science", "Philosophy", "Literature", "Geography", "Math", "Politics", "Religion"]
LANGUAGES = ["en", "fr", "de", "es", "it"]
FORMATS = ["book", "manuscript", "pamphlet", "map", "photograph"]

def generate_manifest(i):
    madoc_id = f"urn:madoc:manifest:{i}"
    
    metadata = []
    # Generate 10-20 random metadata attributes
    for _ in range(random.randint(10, 20)):
        field_type = random.choice(["Author", "Subject", "Format", "Location", "Publisher"])
        if field_type == "Author":
            val = random.choice(AUTHORS)
        elif field_type == "Subject":
            val = random.choice(SUBJECTS)
        elif field_type == "Format":
            val = random.choice(FORMATS)
        else:
            val = f"Random Value {random.randint(1, 100)}"
            
        lang = random.choice(LANGUAGES)
        
        metadata.append({
            "label": {lang: [field_type]},
            "value": {lang: [val]}
        })
        
    payload = {
        "id": madoc_id,
        "cascade": False,
        "resource": {
            "@context": "http://iiif.io/api/presentation/3/context.json",
            "id": f"http://example.org/iiif/manifest/{i}",
            "type": "Manifest",
            "label": {"en": [f"Synthetic Manifest {i}"]},
            "metadata": metadata
        }
    }
    
    return payload

if __name__ == "__main__":
    os.makedirs("synthetic_data", exist_ok=True)
    for i in range(1, 501):
        manifest = generate_manifest(i)
        with open(f"synthetic_data/manifest_{i}.json", "w") as f:
            json.dump(manifest, f, indent=2)
    print("Generated 500 synthetic manifests in synthetic_data/")
