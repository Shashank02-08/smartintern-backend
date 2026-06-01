"""
skill_matcher.py
Matches resume text against internship skills and generates match scores.
"""

import logging

logger = logging.getLogger(__name__)

SKILL_KEYWORDS = [
    'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'php', 'ruby',
    'swift', 'kotlin', 'go', 'rust', 'scala', 'r',
    'html', 'css', 'react', 'angular', 'vue', 'nodejs', 'node.js', 'express',
    'django', 'flask', 'fastapi', 'bootstrap', 'tailwind',
    'mysql', 'postgresql', 'mongodb', 'firebase', 'redis', 'sqlite',
    'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'git', 'github', 'linux',
    'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'scikit-learn',
    'nlp', 'pandas', 'numpy', 'matplotlib', 'data science', 'ai',
    'android', 'ios', 'flutter', 'react native',
    'figma', 'adobe xd', 'photoshop', 'illustrator', 'ui/ux',
    'excel', 'sql', 'rest api', 'graphql', 'agile', 'scrum',
    'communication', 'teamwork', 'leadership', 'problem solving'
]


def extract_skills_from_text(text):
    text_lower = text.lower()
    found_skills = []
    for skill in SKILL_KEYWORDS:
        if skill.lower() in text_lower:
            found_skills.append(skill)
    return found_skills


def calculate_match_score(resume_skills, internship_skills):
    if not internship_skills:
        return 50

    resume_lower = [s.lower() for s in resume_skills]
    internship_lower = [s.lower() for s in internship_skills]

    matched = 0
    for skill in internship_lower:
        if any(skill in r or r in skill for r in resume_lower):
            matched += 1

    score = int((matched / len(internship_lower)) * 100)
    return min(score, 100)


def get_skill_gaps(resume_skills, internship_skills):
    resume_lower = [s.lower() for s in resume_skills]
    gaps = []
    for skill in internship_skills:
        if not any(skill.lower() in r or r in skill.lower() for r in resume_lower):
            gaps.append(skill)
    return gaps


def match_resume_to_internships(resume_text, internships):
    resume_skills = extract_skills_from_text(resume_text)
    logger.info("Extracted %d skills from resume", len(resume_skills))

    matched = []
    for internship in internships:
        internship_skills = internship.get('skills', [])
        score = calculate_match_score(resume_skills, internship_skills)
        gaps = get_skill_gaps(resume_skills, internship_skills)

        internship_copy = dict(internship)
        internship_copy['match_score'] = score
        internship_copy['skill_gaps'] = gaps[:5]
        matched.append(internship_copy)

    matched.sort(key=lambda x: x['match_score'], reverse=True)
    return matched