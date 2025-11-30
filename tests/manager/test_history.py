# tests/manager/test_history.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from ...manager.history import HistoryManager, default_history_format_function
from ...cloggable_list import CloggableList
from ...async_history_dump import AsyncHistoryDumpGenerator


class TestDefaultHistoryFormatFunction:
    """Tests for default_history_format_function."""

    def test_format_commit(self):
        """Test formatting COMMIT history entry."""
        history = {
            "query": "COMMIT",
            "path": "test.db",
            "timestamp": "2024-01-01 12:00:00",
            "params": None,
            "result": None,
        }
        result = default_history_format_function(history)
        assert "[2024-01-01 12:00:00](test.db) : COMMIT" in result

    def test_format_regular_query(self):
        """Test formatting regular query history entry."""
        history = {
            "query": "SELECT * FROM users",
            "path": "test.db",
            "timestamp": "2024-01-01 12:00:00",
            "params": (1,),
            "result": [(1, "Alice")],
        }
        result = default_history_format_function(history)
        assert "[2024-01-01 12:00:00](test.db)" in result
        assert "SELECT * FROM users" in result
        assert "Input: (1,)" in result
        assert "Output: [(1, 'Alice')]" in result

    def test_format_missing_timestamp(self):
        """Test formatting with missing timestamp."""
        history = {
            "query": "SELECT 1",
            "path": "test.db",
            "params": (),
            "result": [(1,)],
        }
        result = default_history_format_function(history)
        assert "[no timestamp]" in result


class TestHistoryManager:
    """Tests for HistoryManager class."""

    def test_init_default(self):
        """Test HistoryManager initialization with defaults."""
        hm = HistoryManager()
        assert hm.history_length == 10
        assert hm.history_tolerance == 5
        assert hm.history is not None
        assert isinstance(hm.history, CloggableList)
        assert hm.history_dump_generator is None

    def test_init_with_custom_values(self):
        """Test HistoryManager initialization with custom values."""
        gen = MagicMock(spec=AsyncHistoryDumpGenerator)
        hm = HistoryManager(
            history_length=20,
            history_tolerance=10,
            history_dump_generator=gen,
        )
        assert hm.history_length == 20
        assert hm.history_tolerance == 10
        assert hm.history_dump_generator is gen

    def test_init_with_none_history_length(self):
        """Test HistoryManager with None history_length disables history."""
        hm = HistoryManager(history_length=None)
        assert hm.history is None
        assert hm.history_length is None

    def test_init_invalid_history_length_raises(self):
        """Test HistoryManager raises ValueError for invalid history_length."""
        with pytest.raises(ValueError):
            HistoryManager(history_length=-1)

    def test_init_invalid_history_tolerance_raises(self):
        """Test HistoryManager raises ValueError for invalid history_tolerance."""
        with pytest.raises(ValueError):
            HistoryManager(history_tolerance=-1)

    def test_validate_none_or_non_neg_int_valid(self):
        """Test _validate_none_or_non_neg_int with valid values."""
        assert HistoryManager._validate_none_or_non_neg_int(0) == 0
        assert HistoryManager._validate_none_or_non_neg_int(10) == 10
        assert HistoryManager._validate_none_or_non_neg_int(None) is None

    def test_validate_none_or_non_neg_int_invalid(self):
        """Test _validate_none_or_non_neg_int with invalid values."""
        with pytest.raises(ValueError):
            HistoryManager._validate_none_or_non_neg_int(-1)
        with pytest.raises(ValueError):
            HistoryManager._validate_none_or_non_neg_int("invalid")

    def test_history_property_setter(self):
        """Test history property setter."""
        hm = HistoryManager()
        new_history = CloggableList(max_length=5, tolerance=2)
        hm.history = new_history
        assert hm.history is new_history

    def test_history_property_setter_none(self):
        """Test history property setter with None."""
        hm = HistoryManager()
        hm.history = None
        assert hm.history is None
        assert hm.history_length is None

    def test_history_property_setter_invalid_raises(self):
        """Test history property setter raises ValueError for invalid type."""
        hm = HistoryManager()
        with pytest.raises(ValueError):
            hm.history = "invalid"

    def test_history_length_setter(self):
        """Test history_length property setter."""
        hm = HistoryManager(history_length=10)
        hm.history_length = 20
        assert hm.history_length == 20

    def test_history_length_setter_none(self):
        """Test history_length property setter with None."""
        hm = HistoryManager(history_length=10)
        hm.history_length = None
        assert hm.history_length is None
        assert hm.history is None

    def test_history_length_setter_creates_history_if_none(self):
        """Test history_length setter creates history if currently None."""
        hm = HistoryManager(history_length=None)
        hm.history_length = 10
        assert hm.history is not None

    def test_history_tolerance_setter(self):
        """Test history_tolerance property setter."""
        hm = HistoryManager()
        hm.history_tolerance = 3
        assert hm.history_tolerance == 3

    def test_history_dump_generator_setter(self):
        """Test history_dump_generator property setter."""
        hm = HistoryManager()
        gen = MagicMock(spec=AsyncHistoryDumpGenerator)
        hm.history_dump_generator = gen
        assert hm.history_dump_generator is gen

    def test_history_dump_generator_setter_none(self):
        """Test history_dump_generator property setter with None."""
        gen = MagicMock(spec=AsyncHistoryDumpGenerator)
        hm = HistoryManager(history_dump_generator=gen)
        hm.history_dump_generator = None
        assert hm.history_dump_generator is None

    def test_history_dump_generator_setter_invalid_raises(self):
        """Test history_dump_generator setter raises ValueError for invalid type."""
        hm = HistoryManager()
        with pytest.raises(ValueError):
            hm.history_dump_generator = "invalid"

    @pytest.mark.asyncio
    async def test_append_returns_early_if_no_history(self):
        """Test append returns early if history is None."""
        hm = HistoryManager(history_length=None)
        await hm.append({"query": "test"})  # Should not raise

    @pytest.mark.asyncio
    async def test_append_returns_early_if_no_generator(self):
        """Test append returns early if history_dump_generator is None."""
        hm = HistoryManager()
        await hm.append({"query": "test"})  # Should not raise

    @pytest.mark.asyncio
    async def test_append_with_generator(self):
        """Test append with history_dump_generator calls create."""
        from ...async_history_dump import AsyncHistoryDump, AsyncHistoryDumpGenerator
        
        gen = MagicMock(spec=AsyncHistoryDumpGenerator)
        mock_dump = MagicMock(spec=AsyncHistoryDump)
        mock_dump.data = "formatted string"  # Non-dict data doesn't get reformatted
        gen.create.return_value = mock_dump

        # Use larger history_length to avoid triggering flush
        hm = HistoryManager(history_dump_generator=gen, history_length=100)
        
        # Directly manipulate to make history non-empty (truthy) but not full
        hm._history.append(MagicMock())
        
        item = {"query": "test", "path": "test.db", "params": (), "result": []}
        
        # Patch flush_to_file to avoid issues with MagicMock dumps
        with patch.object(hm, 'flush_to_file', new_callable=AsyncMock):
            await hm.append(item)
        
        gen.create.assert_called_once_with(item)

    @pytest.mark.asyncio
    async def test_flush_to_file_with_none_history(self):
        """Test flush_to_file returns early if history is None."""
        hm = HistoryManager(history_length=None)
        await hm.flush_to_file()  # Should not raise

    @pytest.mark.asyncio
    async def test_flush_to_file_calls_write_many(self):
        """Test flush_to_file calls AsyncHistoryDump.write_many."""
        hm = HistoryManager(history_length=10)
        mock_dump = MagicMock()
        hm.history.append(mock_dump)

        from ...async_history_dump import AsyncHistoryDump
        with patch.object(AsyncHistoryDump, 'write_many', new_callable=AsyncMock) as mock_write:
            await hm.flush_to_file()
            mock_write.assert_called_once()
