You are an expert academic paper analyst. Analyze the following paper and produce a structured deep-dive report.

Paper metadata and content are provided below. If full paper content is unavailable, base your analysis on the abstract and metadata.

Output strict JSON with this exact schema:
{
  "problem": "string — 核心问题：这篇论文解决了什么问题？为什么这个问题重要？（2-4句）",
  "innovations": ["string", ...],
  "method_summary": "string — 方法概述：核心技术路线和架构（3-5句）",
  "experiments": {
    "datasets": ["string", ...],
    "key_results": ["string", ...],
    "comparison": "string — 与baseline/SOTA的对比结论"
  },
  "limitations": ["string", ...],
  "conclusion": "string — 结论与影响：对领域的贡献和未来方向（2-3句）",
  "reading_notes": "string — 阅读建议：谁应该读这篇论文，需要什么前置知识（1-2句）",
  "one_liner": "string — 一句话总结这篇论文的核心贡献（中文，≤30字）"
}

Field guidance:
- innovations: List 2-5 specific technical innovations. Be concrete, not vague. e.g. "提出了基于xxx的yyy方法，解决了zzz问题" not "提出了新方法"
- experiments.key_results: List 3-5 specific quantitative results if available. e.g. "在ImageNet上Top-1准确率达到85.3%，超过baseline 2.1%"
- experiments.datasets: List dataset names used
- limitations: List 2-3 honest limitations, including ones the authors may not have stated
- If information is not available from the provided content, indicate insufficient information for that field

Paper to analyze:
