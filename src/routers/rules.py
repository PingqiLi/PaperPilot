"""
ArXiv分类参考路由
"""
from fastapi import APIRouter

router = APIRouter()


ARXIV_CATEGORIES = {
    "cs": {
        "cs.AI": "Artificial Intelligence",
        "cs.CL": "Computation and Language",
        "cs.CV": "Computer Vision",
        "cs.LG": "Machine Learning",
        "cs.NE": "Neural and Evolutionary Computing",
        "cs.RO": "Robotics",
        "cs.SE": "Software Engineering",
        "cs.DC": "Distributed Computing",
        "cs.IR": "Information Retrieval",
        "cs.PL": "Programming Languages",
    },
    "stat": {
        "stat.ML": "Machine Learning",
        "stat.TH": "Statistics Theory",
    },
    "eess": {
        "eess.AS": "Audio and Speech Processing",
        "eess.IV": "Image and Video Processing",
    },
}


@router.get("/categories")
async def get_arxiv_categories():
    return ARXIV_CATEGORIES
