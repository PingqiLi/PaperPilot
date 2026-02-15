
"""
两阶段过滤服务 - 关键词初筛 + OpenClaw语义精排
"""
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog

from ..models import Paper, RuleSet, PaperRuleSet
from ..database import get_db_context
from .openclaw_service import openclaw_client
from .arxiv_fetcher import ArxivFetcher
from .semantic_scholar import semantic_scholar

logger = structlog.get_logger(__name__)


# 关键词扩展Prompt
KEYWORD_EXPANSION_PROMPT = """你是一个学术论文检索助手。用户对以下主题感兴趣：

{query}

请生成10-15个相关的英文关键词或短语，用于在ArXiv上搜索相关论文。
关键词应该涵盖：
- 核心概念
- 相关技术
- 常见方法名称
- 应用领域

输出格式（JSON）：
{{
    "keywords": ["keyword1", "keyword2", ...]
}}
"""


# 语义评分Prompt
SEMANTIC_SCORING_PROMPT = """你是一个学术论文评估助手。请评估这篇论文与用户自定义Topic的相关性。

## 用户Topic描述 (Topic Description)
{query}

## 论文信息
**标题**: {title}
**摘要**: {abstract}

## 评分任务
请仔细阅读用户的Topic描述，并判断论文内容是否实质性地符合该Topic。
评分标准 (1-10分)：
- 1-3分：不相关或仅关键词匹配但内容不符
- 4-5分：边缘相关，或者是该领域的通用综述/无关应用
- 6-7分：相关，解决了Topic中的部分问题或使用了相关技术
- 8-9分：高度相关，直接针对Topic的核心痛点
- 10分：完全匹配，正是用户想要的必读论文

## 输出格式 (Strict JSON)
{{
    "score": 8, 
    "reason": "简短说明理由（中文），指出论文与Topic的具体的契合点或偏差。"
}}
"""


class TwoStageFilter:
    """两阶段过滤器 (OpenClaw集成版)"""
    
    def __init__(self):
        self.fetcher = ArxivFetcher()
        self.client = openclaw_client
    
    def _clean_json_response(self, response: str) -> str:
        """清理并提取JSON字符串"""
        if not isinstance(response, str):
            return str(response)
        cleaned = response.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0]
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0]
        return cleaned.strip()

    async def expand_keywords(self, semantic_query: str) -> List[str]:
        """
        阶段0：使用Agent扩展用户主题为关键词列表
        """
        try:
            prompt = KEYWORD_EXPANSION_PROMPT.format(query=semantic_query)
            
            # 调用Agent
            system_instruction = "You are a helpful assistant. Output must be strictly valid JSON."
            response = await self.client.send_agent_task(
                task=prompt,
                agent_id="main",
                system_prompt=system_instruction,
                wait=True
            )
            
            # 解析结果
            if isinstance(response, dict) and "response" in response:
                 content = response["response"]
            else:
                 content = response
                 
            if isinstance(content, dict):
                result = content
            else:
                cleaned_json = self._clean_json_response(str(content))
                result = json.loads(cleaned_json)

            keywords = result.get("keywords", [])
            logger.info("Keywords expanded", query=semantic_query, count=len(keywords))
            return keywords
        except Exception as e:
            logger.error("Keyword expansion failed", error=str(e))
            return []
    
    def stage1_keyword_filter(
        self,
        papers: List[Dict[str, Any]],
        keywords: List[str],
        exclude_keywords: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        阶段1：关键词初筛（快速）
        返回包含任一关键词的论文
        """
        if not keywords:
            return papers
        
        filtered = []
        exclude_keywords = exclude_keywords or []
        
        for paper in papers:
            text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
            
            # 排除关键词检查
            if any(kw.lower() in text for kw in exclude_keywords):
                continue
            
            # 包含关键词检查
            if any(kw.lower() in text for kw in keywords):
                filtered.append(paper)
        
        logger.info(
            "Stage 1 filter completed",
            input_count=len(papers),
            output_count=len(filtered)
        )
        return filtered
    
    async def stage2_semantic_scoring(
        self,
        paper: Paper,
        semantic_query: str
    ) -> Dict[str, Any]:
        """
        阶段2：Agent语义精排（单篇）
        """
        try:
            prompt = SEMANTIC_SCORING_PROMPT.format(
                query=semantic_query,
                title=paper.title,
                abstract=paper.abstract or ""
            )
            
            # 调用Agent
            system_instruction = "You are a helpful assistant. Output must be strictly valid JSON."
            response = await self.client.send_agent_task(
                task=prompt,
                agent_id="main",
                system_prompt=system_instruction,
                wait=True
            )
            
            # 解析结果
            if isinstance(response, dict) and "response" in response:
                 content = response["response"]
            else:
                 content = response

            if isinstance(content, dict):
                result = content
            else:
                cleaned_json = self._clean_json_response(str(content))
                result = json.loads(cleaned_json)
            
            score = min(10, max(1, result.get("score", 5)))
            reason = result.get("reason", "")
            
            return {"score": score, "reason": reason}
            
        except Exception as e:
            logger.error("Semantic scoring failed", paper_id=paper.id, error=str(e))
            return {"score": 5, "reason": "评分失败"}
    
    async def process_ruleset(
        self,
        ruleset: RuleSet,
        max_papers: int = 500,
        score_threshold: float = 5.0
    ) -> Dict[str, int]:
        """
        处理单个规则集：完整的两阶段过滤流程
        """
        logger.info("Processing ruleset", ruleset_id=ruleset.id, name=ruleset.name)
        
        # 1. 扩展关键词（如果有语义查询）
        expanded_keywords = []
        if ruleset.semantic_query:
            expanded_keywords = await self.expand_keywords(ruleset.semantic_query)
        
        # 合并配置的关键词和扩展的关键词
        all_keywords = list(set(
            (ruleset.keywords_include or []) + expanded_keywords
        ))
        
        # 2. 从ArXiv抓取论文
        papers = self.fetcher.fetch(
            categories=ruleset.categories or ["cs.AI", "cs.LG"],
            max_results=max_papers,
            date_range=ruleset.date_range_days or 30
        )
        
        # 3. 阶段1：关键词初筛
        filtered_papers = self.stage1_keyword_filter(
            papers,
            all_keywords,
            ruleset.keywords_exclude or []
        )
        
        # 4. 保存论文到数据库并关联规则集
        saved_count = 0
        scored_count = 0
        
        with get_db_context() as db:
            for paper_data in filtered_papers:
                # 查找或创建论文
                existing = db.query(Paper).filter(
                    Paper.arxiv_id == paper_data["arxiv_id"]
                ).first()
                
                if not existing:
                    # 注意：fetcher返回的authors是列表，需要转字符串？
                    # 假设fetcher返回的与Model匹配
                    if isinstance(paper_data.get("authors"), list):
                        paper_data["authors"] = ", ".join(paper_data["authors"])
                    
                    paper = Paper(**paper_data)
                    db.add(paper)
                    db.flush()
                    saved_count += 1
                else:
                    paper = existing
                
                # 创建论文-规则集关联
                assoc = db.query(PaperRuleSet).filter(
                    PaperRuleSet.paper_id == paper.id,
                    PaperRuleSet.ruleset_id == ruleset.id
                ).first()
                
                if not assoc:
                    assoc = PaperRuleSet(
                        paper_id=paper.id,
                        ruleset_id=ruleset.id,
                        is_scored=False
                    )
                    db.add(assoc)
            
            # 更新规则集状态
            ruleset.last_fetch_at = datetime.utcnow()
            ruleset.expanded_keywords = expanded_keywords
            
            db.commit()
        
        logger.info(
            "Ruleset processing completed",
            ruleset_id=ruleset.id,
            fetched=len(papers),
            filtered=len(filtered_papers),
            saved=saved_count
        )
        
        return {
            "fetched": len(papers),
            "filtered": len(filtered_papers),
            "saved": saved_count
        }
    
    async def batch_score_papers(
        self,
        ruleset_id: int,
        batch_size: int = 10,
        score_threshold: float = 5.0
    ) -> int:
        """
        批量对规则集下未评分的论文进行语义评分（离线任务）
        """
        scored_count = 0
        
        with get_db_context() as db:
            ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
            if not ruleset:
                return 0
            
            # 获取未评分的论文
            unscored = db.query(PaperRuleSet).filter(
                PaperRuleSet.ruleset_id == ruleset_id,
                PaperRuleSet.is_scored == False
            ).limit(batch_size).all()
            
            for assoc in unscored:
                paper = db.query(Paper).filter(Paper.id == assoc.paper_id).first()
                if not paper:
                    continue
                
                # Agent评分
                # 优先使用 topic_description (长文本)，其次是 semantic_query (短语)，最后是 name
                query_text = ruleset.topic_description or ruleset.semantic_query or ruleset.name
                
                result = await self.stage2_semantic_scoring(
                    paper, query_text
                )
                
                assoc.semantic_score = result["score"]
                assoc.score_reason = result["reason"]
                assoc.is_scored = True
                assoc.scored_at = datetime.utcnow()
                scored_count += 1
                
                logger.debug(
                    "Paper scored",
                    paper_id=paper.id,
                    score=result["score"]
                )
            
            # 更新规则集统计
            ruleset.total_papers = db.query(PaperRuleSet).filter(
                PaperRuleSet.ruleset_id == ruleset_id,
                PaperRuleSet.semantic_score >= score_threshold
            ).count()
            
            db.commit()
        
        logger.info("Batch scoring completed", ruleset_id=ruleset_id, scored=scored_count)
        return scored_count


    async def rapid_screen_ruleset(
        self,
        ruleset_id: int,
        max_results: int = 50,
        year_start: int = 2023
    ) -> Dict[str, Any]:
        """
        使用Semantic Scholar进行快速主题筛选 (Rapid Screening)
        流程：S2搜索 -> Paper入库 -> Agent评分
        """
        logger.info("Starting rapid screening", ruleset_id=ruleset_id)
        
        with get_db_context() as db:
            ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
            if not ruleset:
                raise ValueError(f"RuleSet {ruleset_id} not found")
            
            # 1. 确定搜索关键词
            # 优先使用 S2 Semantic Query，如果没有，则尝试从 Topic Description 提取或使用 RuleSet Name
            query = ruleset.semantic_query or ruleset.name
            
            # 2. S2 搜索
            papers_data = await semantic_scholar.search_papers(
                query=query,
                limit=max_results,
                year_start=year_start
            )
            
            logger.info("S2 search returned", count=len(papers_data), query=query)
            
            saved_count = 0
            scored_count = 0
            
            for p_data in papers_data:
                # 3. Paper 入库/更新
                arxiv_id = p_data.get("externalIds", {}).get("ArXiv")
                s2_id = p_data.get("paperId")
                
                # 如果没有ArXiv ID，生成一个伪ID "s2:{paperId}"
                paper_identity = arxiv_id or f"s2:{s2_id}"
                
                existing_paper = db.query(Paper).filter(
                    Paper.arxiv_id == paper_identity
                ).first()
                
                if not existing_paper:
                    # 创建新 Paper
                    authors = p_data.get("authors", [])
                    if isinstance(authors, list):
                        # S2 returns objects like {'authorId': '...', 'name': '...'}
                        authors = [a.get("name", "") for a in authors if isinstance(a, dict)]
                    
                    paper = Paper(
                        arxiv_id=paper_identity,
                        title=p_data.get("title"),
                        abstract=p_data.get("abstract"),
                        authors=authors,
                        published_date=datetime.strptime(p_data.get("publicationDate"), "%Y-%m-%d") if p_data.get("publicationDate") else datetime(p_data.get("year", year_start), 1, 1),
                        semantic_scholar_id=s2_id,
                        citation_count=p_data.get("citationCount", 0),
                        citation_updated_at=datetime.utcnow(),
                        is_processed=False # 标记为未处理，以便后续Deep Analysis
                    )
                    db.add(paper)
                    db.flush() # 获取 ID
                    saved_count += 1
                else:
                    paper = existing_paper
                    # 更新引用数
                    if p_data.get("citationCount"):
                        paper.citation_count = p_data.get("citationCount")
                        paper.citation_updated_at = datetime.utcnow()
                
                # 4. 关联 RuleSet
                assoc = db.query(PaperRuleSet).filter(
                    PaperRuleSet.paper_id == paper.id,
                    PaperRuleSet.ruleset_id == ruleset.id
                ).first()
                
                if not assoc:
                    assoc = PaperRuleSet(
                        paper_id=paper.id,
                        ruleset_id=ruleset.id,
                        is_scored=False
                    )
                    db.add(assoc)
                    db.flush()
                
                # 5. Agent 评分 (如果尚未评分)
                if not assoc.is_scored:
                    query_text = ruleset.topic_description or ruleset.semantic_query or ruleset.name
                    
                    # 调用评分逻辑
                    result = await self.stage2_semantic_scoring(
                        paper, query_text
                    )
                    
                    assoc.semantic_score = result["score"]
                    assoc.score_reason = result["reason"]
                    assoc.is_scored = True
                    assoc.scored_at = datetime.utcnow()
                    scored_count += 1
                    
                    # 实时提交
                    # db.commit() # 也可以批量提交
            
            # 更新 RuleSet 统计
            ruleset.last_fetch_at = datetime.utcnow()
            db.commit()
            
            return {
                "fetched": len(papers_data),
                "saved": saved_count,
                "scored": scored_count
            }


