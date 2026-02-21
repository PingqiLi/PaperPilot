from src.services.arxiv import ArxivService


class TestBuildQuery:
    def setup_method(self):
        self.svc = ArxivService()

    def test_single_category_single_keyword(self):
        q = self.svc._build_query(["cs.LG"], ["quantization"])
        assert q == "cat:cs.LG AND abs:quantization"

    def test_multiple_categories(self):
        q = self.svc._build_query(["cs.LG", "cs.CL"], ["quantization"])
        assert "(cat:cs.LG OR cat:cs.CL)" in q
        assert "abs:quantization" in q

    def test_multi_word_keyword_splits(self):
        q = self.svc._build_query(["cs.LG"], ["reinforcement learning"])
        assert "abs:reinforcement" in q
        assert "abs:learning" in q

    def test_short_words_in_multi_word_filtered(self):
        q = self.svc._build_query(["cs.LG"], ["RL in LLM"])
        assert "abs:LLM" in q
        assert "abs:in" not in q

    def test_empty_categories(self):
        q = self.svc._build_query([], ["quantization"])
        assert q == "abs:quantization"
        assert "cat:" not in q

    def test_date_filter(self):
        q = self.svc._build_query(["cs.LG"], ["test"], date_from="202501010000")
        assert "submittedDate:[202501010000 TO 299912312359]" in q

    def test_date_filter_both(self):
        q = self.svc._build_query(
            ["cs.LG"], ["test"],
            date_from="202501010000", date_to="202502010000",
        )
        assert "submittedDate:[202501010000 TO 202502010000]" in q


class TestKeywordCombinations:
    def setup_method(self):
        self.svc = ArxivService()

    def test_empty_keywords(self):
        assert self.svc.generate_keyword_combinations([]) == []

    def test_single_keyword(self):
        result = self.svc.generate_keyword_combinations(["quantization"])
        assert result == [["quantization"]]

    def test_two_keywords(self):
        result = self.svc.generate_keyword_combinations(["a", "b"])
        assert result == [["a", "b"]]

    def test_three_keywords_generates_pairs(self):
        result = self.svc.generate_keyword_combinations(["a", "b", "c"])
        assert len(result) == 3
        assert ["a", "b"] in result
        assert ["a", "c"] in result
        assert ["b", "c"] in result

    def test_max_combinations_cap(self):
        keywords = ["a", "b", "c", "d", "e", "f"]
        result = self.svc.generate_keyword_combinations(keywords, max_combinations=3)
        assert len(result) == 3

    def test_uses_first_five_keywords(self):
        keywords = ["a", "b", "c", "d", "e", "f", "g"]
        result = self.svc.generate_keyword_combinations(keywords, max_combinations=20)
        all_kws = {kw for combo in result for kw in combo}
        assert "f" not in all_kws
        assert "g" not in all_kws


class TestParseEntry:
    def setup_method(self):
        self.svc = ArxivService()

    def test_parse_valid_entry(self):
        import xml.etree.ElementTree as ET
        xml = """<entry xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
            <id>http://arxiv.org/abs/2602.13953v1</id>
            <title>QuRL: Quantized Reinforcement Learning for LLMs</title>
            <summary>We propose QuRL for efficient post-training.</summary>
            <author><name>John Doe</name></author>
            <author><name>Jane Smith</name></author>
            <published>2026-02-10T00:00:00Z</published>
            <arxiv:primary_category term="cs.LG"/>
            <category term="cs.LG"/>
            <category term="cs.CL"/>
        </entry>"""
        entry = ET.fromstring(xml)
        result = self.svc._parse_entry(entry)

        assert result is not None
        assert result["externalIds"]["ArXiv"] == "2602.13953"
        assert "QuRL" in result["title"]
        assert result["year"] == 2026
        assert result["publicationDate"] == "2026-02-10"
        assert len(result["authors"]) == 2
        assert result["citationCount"] == 0
        assert result["_arxiv_primary_category"] == "cs.LG"
        assert "cs.CL" in result["_arxiv_categories"]
        assert result["_source"] == "arxiv"

    def test_parse_strips_version(self):
        import xml.etree.ElementTree as ET
        xml = """<entry xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
            <id>http://arxiv.org/abs/2510.11696v3</id>
            <title>Test</title>
            <summary>Abstract</summary>
            <published>2025-10-15T00:00:00Z</published>
        </entry>"""
        entry = ET.fromstring(xml)
        result = self.svc._parse_entry(entry)
        assert result["externalIds"]["ArXiv"] == "2510.11696"

    def test_parse_invalid_entry_no_abs(self):
        import xml.etree.ElementTree as ET
        xml = """<entry xmlns="http://www.w3.org/2005/Atom">
            <id>http://arxiv.org/api/errors</id>
            <title>Error</title>
            <summary>Error</summary>
        </entry>"""
        entry = ET.fromstring(xml)
        result = self.svc._parse_entry(entry)
        assert result is None
