"""
skill_matcher.py
Matches resume text against internship skills and generates match scores.
"""

import re
import logging
from typing import list, dict

logger = logging.getLogger(__name__)

# Common tech skills to look for
SKILL_KEYWORDS = [
    # Programming Languages
    'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'php', 'ruby',
    'swift', 'kotlin', 'go', 'rust', 'scala', 'r',
    # Web
    'html', 'css', 'react', 'angular', 'vue', 'nodejs', 'node.js', 'express',
    'django', 'flask', 'fastapi', 'bootstrap', 'tailwind',
    # Database
    'mysql', 'postgresql', 'mongodb', 'firebase', 'redis', 'sqlite',
    # Cloud & DevOps
    'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'git', 'github', 'linux',
    # AI/ML
    'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'scikit-learn',
    'nlp', 'pandas', 'numpy', 'matplotlib', 'data science', 'ai',
    # Mobile
    'android', 'ios', 'flutter', 'react native',
    # Design
    'figma', 'adobe xd', 'photoshop', 'illustrator', 'ui/ux',
    # Other
    'excel', 'sql', 'rest api', 'graphql', 'agile', 'scrum',
    'communication', 'teamwork', 'leadership', 'problem solving'
]


def extract_skills_from_text(text: str) -> list[str]:
    """Extract skills from resume text."""
    text_lower = text.lower()
    found_skills = []
    for skill in SKILL_KEYWORDS:
        if skill.lower() in text_lower:
            found_skills.append(skill)
    return found_skills


def calculate_match_score(resume_skills: list[str], internship_skills: list[str]) -> int:
    """
    Calculate match percentage between resume skills and internship skills.
    Returns a score between 0 and 100.
    """
    if not internship_skills:
        return 50  # neutral score if no skills listed

    resume_lower = [s.lower() for s in resume_skills]
    internship_lower = [s.lower() for s in internship_skills]

    matched = 0
    for skill in internship_lower:
        # Check exact match or partial match
        if any(skill in r or r in skill for r in resume_lower):
            matched += 1

    score = int((matched / len(internship_lower)) * 100)
    return min(score, 100)


def get_skill_gaps(resume_skills: list[str], internship_skills: list[str]) -> list[str]:
    """Return skills required by internship but missing from resume."""
    resume_lower = [s.lower() for s in resume_skills]
    gaps = []
    for skill in internship_skills:
        if not any(skill.lower() in r or r in skill.lower() for r in resume_lower):
            gaps.append(skill)
    return gaps


def match_resume_to_internships(resume_text: str, internships: list[dict]) -> list[dict]:
    """
    Match resume against all internships and return ranked results.
    """
    resume_skills = extract_skills_from_text(resume_text)
    logger.info(f"Extracted {len(resume_skills)} skills from resume")

    matched = []
    for internship in internships:
        internship_skills = internship.get('skills', [])
        score = calculate_match_score(resume_skills, internship_skills)
        gaps = get_skill_gaps(resume_skills, internship_skills)

        internship_copy = dict(internship)
        internship_copy['match_score'] = score
        internship_copy['skill_gaps'] = gaps[:5]  # top 5 gaps
        matched.append(internship_copy)

    # Sort by match score
    matched.sort(key=lambda x: x['match_score'], reverse=True)
    return matched