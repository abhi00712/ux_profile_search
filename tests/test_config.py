from scripts.config import load_config


def test_load_config_reads_searches_and_location():
    cfg = load_config("config.yaml")

    assert [s["max_pages"] for s in cfg["searches"]] == [3, 2]
    assert cfg["location"]["city_keywords"] == ["bengaluru", "bangalore"]
