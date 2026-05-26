from src.pipeline.nlp import (
    analyse_sentiment,
    count_term_frequencies,
    detect_topics,
    extract_keywords,
)


class TestDetectTopics:
    def test_dpe_topic(self):
        topics = detect_topics("Le DPE du logement est réformé en 2026")
        assert "dpe_audit" in topics

    def test_aides_topic(self):
        topics = detect_topics("MaPrimeRénov est disponible pour les ménages modestes")
        assert "aides_financières" in topics

    def test_reglementation_topic(self):
        topics = detect_topics("Un nouveau décret sur les obligations de rénovation")
        assert "réglementation" in topics

    def test_renovation_geste_topic(self):
        topics = detect_topics("Isolation des combles et pompe à chaleur subventionnées")
        assert "rénovation_geste" in topics

    def test_marche_immobilier_topic(self):
        topics = detect_topics("Le prix de vente des logements énergivores chute")
        assert "marché_immobilier" in topics

    def test_etudes_topic(self):
        topics = detect_topics("Étude de l'observatoire sur les données DPE 2025")
        assert "études_données" in topics

    def test_multiple_topics(self):
        topics = detect_topics("Le DPE impacte la vente immobilière selon une étude ADEME")
        assert len(topics) >= 2

    def test_unknown_returns_general(self):
        topics = detect_topics("Recette de tarte aux pommes")
        assert topics == ["général"]


class TestAnalyseSentiment:
    def test_positive_text(self):
        score, label = analyse_sentiment("Excellent résultat, très positif pour les propriétaires")
        if score is not None:
            assert label in ("positive", "neutral")

    def test_negative_text(self):
        score, label = analyse_sentiment("Catastrophe, mauvais résultats, problèmes graves")
        if score is not None:
            assert label in ("negative", "neutral")

    def test_empty_text_returns_none(self):
        score, label = analyse_sentiment("")
        assert score is None
        assert label is None

    def test_returns_float_score(self):
        score, label = analyse_sentiment("Rénovation énergétique en France")
        if score is not None:
            assert isinstance(score, float)
            assert -1.0 <= score <= 1.0

    def test_label_is_valid(self):
        score, label = analyse_sentiment("Le marché immobilier évolue")
        if label is not None:
            assert label in ("positive", "negative", "neutral")


class TestExtractKeywords:
    def test_returns_list(self):
        result = extract_keywords("Rénovation énergétique et DPE en France")
        assert isinstance(result, list)

    def test_respects_top_n(self):
        text = "DPE rénovation isolation pompe chaleur fenêtre combles chauffage vmc audit"
        result = extract_keywords(text, top_n=3)
        assert len(result) <= 3

    def test_empty_text_returns_empty(self):
        result = extract_keywords("")
        assert result == []

    def test_stopwords_not_in_keywords(self):
        result = extract_keywords("Le DPE est un diagnostic de performance énergétique")
        for kw in result:
            assert kw not in ("le", "est", "un", "de")


class TestCountTermFrequencies:
    def test_returns_dict(self):
        texts = ["DPE rénovation", "DPE isolation", "rénovation thermique"]
        result = count_term_frequencies(texts)
        assert isinstance(result, dict)

    def test_sorted_by_frequency(self):
        texts = ["DPE DPE DPE rénovation", "DPE isolation", "rénovation rénovation"]
        result = count_term_frequencies(texts, top_n=10)
        values = list(result.values())
        assert values == sorted(values, reverse=True)

    def test_empty_list_returns_empty(self):
        assert count_term_frequencies([]) == {}

    def test_respects_top_n(self):
        texts = ["dpe rénovation isolation pompe chaleur fenêtre combles chauffage vmc audit"] * 5
        result = count_term_frequencies(texts, top_n=5)
        assert len(result) <= 5
