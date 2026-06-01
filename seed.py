from pymongo import MongoClient
from dotenv import load_dotenv
import os
import json

load_dotenv()

client = MongoClient(os.getenv('MONGO_URI'))
db = client['smartintern']
internships = db['internships']

# Clear existing data
internships.delete_many({})

# Load from JSON file
with open('internships.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Clean up skills field — convert string to list
for item in data:
    skills = item.get('skills', [])
    if isinstance(skills, str):
        skills = skills.strip('[]').split(',')
        skills = [s.strip().strip('"').strip("'") for s in skills if s.strip()]
        # Remove long sentences — keep only short skill keywords
        skills = [s for s in skills if len(s) < 30]
    item['skills'] = skills
    # Rename organization to company for consistency
    item['company'] = item.pop('organization', '')

internships.insert_many(data)
print(f"✅ {len(data)} internships seeded successfully!")