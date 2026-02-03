"""
Unit tests for Champions utility module.
"""
import pytest

from src.utils.champions import (
    CHAMPIONS, CHAMPION_TAGS,
    get_champion_name, get_champion_id, get_champion_by_id,
    get_all_champions, get_champions_by_tag, get_position_champions
)


@pytest.mark.unit
class TestChampionsData:
    """Tests for champion data structures."""

    def test_champions_dict_not_empty(self):
        """Test that CHAMPIONS dict is not empty."""
        assert len(CHAMPIONS) > 0

    def test_champion_tags_dict_not_empty(self):
        """Test that CHAMPION_TAGS dict is not empty."""
        assert len(CHAMPION_TAGS) > 0

    def test_champion_ids_are_integers(self):
        """Test that all champion IDs are integers."""
        for champion_id in CHAMPIONS.keys():
            assert isinstance(champion_id, int)

    def test_champion_names_are_strings(self):
        """Test that all champion names are strings."""
        for champion_name in CHAMPIONS.values():
            assert isinstance(champion_name, str)


@pytest.mark.unit
class TestGetChampionName:
    """Tests for get_champion_name function."""

    def test_get_existing_champion_name(self):
        """Test getting name for existing champion."""
        name = get_champion_name(1)
        assert name == 'Annie'

    def test_get_nonexistent_champion_name(self):
        """Test getting name for nonexistent champion."""
        name = get_champion_name(999999)
        assert 'Unknown' in name
        assert '999999' in name

    def test_get_champion_name_case(self):
        """Test champion name casing."""
        name = get_champion_name(1)
        assert name == 'Annie'  # Proper case


@pytest.mark.unit
class TestGetChampionId:
    """Tests for get_champion_id function."""

    def test_get_existing_champion_id(self):
        """Test getting ID for existing champion."""
        champion_id = get_champion_id('Annie')
        assert champion_id == 1

    def test_get_champion_id_case_insensitive(self):
        """Test that champion ID lookup is case-insensitive."""
        id1 = get_champion_id('annie')
        id2 = get_champion_id('ANNIE')
        id3 = get_champion_id('Annie')
        assert id1 == id2 == id3 == 1

    def test_get_nonexistent_champion_id(self):
        """Test getting ID for nonexistent champion."""
        champion_id = get_champion_id('NonExistentChampion')
        assert champion_id is None


@pytest.mark.unit
class TestGetChampionById:
    """Tests for get_champion_by_id function."""

    def test_get_existing_champion_by_id(self):
        """Test getting champion data for existing champion."""
        champion = get_champion_by_id(1)
        assert champion['id'] == 1
        assert champion['name'] == 'Annie'
        assert 'tags' in champion

    def test_get_nonexistent_champion_by_id(self):
        """Test getting champion data for nonexistent champion."""
        champion = get_champion_by_id(999999)
        assert 'Unknown' in champion['name']


@pytest.mark.unit
class TestGetAllChampions:
    """Tests for get_all_champions function."""

    def test_get_all_champions_returns_list(self):
        """Test that get_all_champions returns a list."""
        champions = get_all_champions()
        assert isinstance(champions, list)

    def test_get_all_champions_structure(self):
        """Test structure of returned champions."""
        champions = get_all_champions()
        if champions:
            champion = champions[0]
            assert 'id' in champion
            assert 'name' in champion
            assert 'tags' in champion

    def test_get_all_champions_count(self):
        """Test that all champions are returned."""
        champions = get_all_champions()
        assert len(champions) == len(CHAMPIONS)


@pytest.mark.unit
class TestGetChampionsByTag:
    """Tests for get_champions_by_tag function."""

    def test_get_mage_champions(self):
        """Test getting mage champions."""
        mages = get_champions_by_tag('mage')
        assert isinstance(mages, list)
        if mages:
            assert 'mage' in mages[0]['tags']

    def test_get_fighter_champions(self):
        """Test getting fighter champions."""
        fighters = get_champions_by_tag('fighter')
        assert isinstance(fighters, list)
        if fighters:
            assert 'fighter' in fighters[0]['tags']

    def test_get_support_champions(self):
        """Test getting support champions."""
        supports = get_champions_by_tag('support')
        assert isinstance(supports, list)
        if supports:
            assert 'support' in supports[0]['tags']

    def test_get_champions_by_tag_case_insensitive(self):
        """Test that tag lookup is case-insensitive."""
        mages1 = get_champions_by_tag('mage')
        mages2 = get_champions_by_tag('MAGE')
        mages3 = get_champions_by_tag('Mage')
        assert len(mages1) == len(mages2) == len(mages3)

    def test_get_champions_by_nonexistent_tag(self):
        """Test getting champions with nonexistent tag."""
        champions = get_champions_by_tag('nonexistent')
        assert champions == []


@pytest.mark.unit
class TestGetPositionChampions:
    """Tests for get_position_champions function."""

    def test_get_top_champions(self):
        """Test getting top lane champions."""
        top_champs = get_position_champions('top')
        assert isinstance(top_champs, list)
        if top_champs:
            # Should include fighters and tanks
            assert len(top_champs) > 0

    def test_get_jungle_champions(self):
        """Test getting jungle champions."""
        jungle_champs = get_position_champions('jungle')
        assert isinstance(jungle_champs, list)
        if jungle_champs:
            assert len(jungle_champs) > 0

    def test_get_mid_champions(self):
        """Test getting mid lane champions."""
        mid_champs = get_position_champions('mid')
        assert isinstance(mid_champs, list)
        if mid_champs:
            assert len(mid_champs) > 0

    def test_get_adc_champions(self):
        """Test getting ADC champions."""
        adc_champs = get_position_champions('adc')
        assert isinstance(adc_champs, list)
        if adc_champs:
            # Should be mostly marksmen
            assert len(adc_champs) > 0

    def test_get_support_champions(self):
        """Test getting support champions."""
        support_champs = get_position_champions('support')
        assert isinstance(support_champs, list)
        if support_champs:
            assert len(support_champs) > 0

    def test_get_position_champions_case_insensitive(self):
        """Test that position lookup is case-insensitive."""
        top1 = get_position_champions('top')
        top2 = get_position_champions('TOP')
        top3 = get_position_champions('Top')
        assert len(top1) == len(top2) == len(top3)

    def test_get_position_champions_invalid(self):
        """Test getting champions for invalid position."""
        champs = get_position_champions('invalid')
        # Should return all champions for invalid position
        assert isinstance(champs, list)
        assert len(champs) > 0
