# tests/manager/test_transaction_status.py
"""Tests for Transaction succeeded and failed properties."""
import pytest
from ...manager.manager import Manager


class TestTransactionStatus:
    """Tests for Transaction.succeeded and Transaction.failed properties."""
    
    @pytest.mark.asyncio
    async def test_succeeded_property_after_commit(self, tmp_path):
        """Test that succeeded property is True after successful commit."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (id INTEGER)", commit=True)
        
        async with manager.Transaction(db_path, autocommit=True) as txn:
            await txn.execute("INSERT INTO test VALUES (1)")
        
        # After __aexit__, succeeded should be True
        assert txn.succeeded is True
        assert txn.failed is False
        
        await manager.disconnect_all()
    
    @pytest.mark.asyncio
    async def test_failed_property_after_rollback(self, tmp_path):
        """Test that failed property is True after rollback due to exception."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (id INTEGER)", commit=True)
        
        txn = manager.Transaction(db_path, autocommit=True)
        try:
            async with txn:
                await txn.execute("INSERT INTO test VALUES (1)")
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # After __aexit__ with exception, succeeded should be False
        assert txn.succeeded is False
        assert txn.failed is True
        
        await manager.disconnect_all()
    
    @pytest.mark.asyncio
    async def test_failed_property_with_autocommit_false(self, tmp_path):
        """Test that failed property is True when autocommit=False (no commit)."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (id INTEGER)", commit=True)
        
        async with manager.Transaction(db_path, autocommit=False) as txn:
            await txn.execute("INSERT INTO test VALUES (1)")
        
        # With autocommit=False, transaction is rolled back
        assert txn.succeeded is False
        assert txn.failed is True
        
        await manager.disconnect_all()
    
    @pytest.mark.asyncio
    async def test_status_none_before_aexit(self, tmp_path):
        """Test that status properties are None before transaction exits."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (id INTEGER)", commit=True)
        
        async with manager.Transaction(db_path, autocommit=True) as txn:
            # During transaction, status should be None
            assert txn.succeeded is None
            assert txn.failed is None
            await txn.execute("INSERT INTO test VALUES (1)")
            # Still None until __aexit__
            assert txn.succeeded is None
            assert txn.failed is None
        
        # After __aexit__, status should be set
        assert txn.succeeded is True
        assert txn.failed is False
        
        await manager.disconnect_all()
    
    @pytest.mark.asyncio
    async def test_status_accessible_for_followup_logic(self, tmp_path):
        """Test using transaction status for follow-up logic."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (id INTEGER)", commit=True)
        await manager.execute(db_path, "CREATE TABLE log (status TEXT)", commit=True)
        
        # Successful transaction
        async with manager.Transaction(db_path, autocommit=True) as txn:
            await txn.execute("INSERT INTO test VALUES (1)")
        
        # Use transaction status for follow-up
        if txn.succeeded:
            await manager.execute(
                db_path,
                "INSERT INTO log VALUES ('success')",
                commit=True
            )
        
        # Failed transaction
        txn2 = manager.Transaction(db_path, autocommit=True)
        try:
            async with txn2:
                await txn2.execute("INSERT INTO test VALUES (2)")
                raise RuntimeError("Simulated error")
        except RuntimeError:
            pass
        
        # Use transaction status for follow-up
        if not txn2.succeeded:
            await manager.execute(
                db_path,
                "INSERT INTO log VALUES ('failed')",
                commit=True
            )
        
        # Verify log entries
        result = await manager.execute(db_path, "SELECT * FROM log")
        assert len(result) == 2
        assert result[0][0] == 'success'
        assert result[1][0] == 'failed'
        
        await manager.disconnect_all()
    
    @pytest.mark.asyncio
    async def test_multiple_transactions_separate_status(self, tmp_path):
        """Test that multiple transactions maintain separate status."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (id INTEGER)", commit=True)
        
        # First transaction - succeeds
        async with manager.Transaction(db_path, autocommit=True) as txn1:
            await txn1.execute("INSERT INTO test VALUES (1)")
        
        # Second transaction - fails
        txn2 = manager.Transaction(db_path, autocommit=True)
        try:
            async with txn2:
                await txn2.execute("INSERT INTO test VALUES (2)")
                raise ValueError("Error")
        except ValueError:
            pass
        
        # Both should maintain their own status
        assert txn1.succeeded is True
        assert txn1.failed is False
        assert txn2.succeeded is False
        assert txn2.failed is True
        
        await manager.disconnect_all()
