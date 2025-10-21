# ABOUTME: Unit tests for MemoryEdge model validation and temporal consistency.
# ABOUTME: Tests memory metadata, corruption tracking, and valid_at/invalid_at relationship.

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from src.models.memory_edge import MemoryEdge, MemoryType, CorruptionType, CorruptionConfig


class TestMemoryEdge:
    """Test suite for MemoryEdge model"""

    def test_valid_memory_edge_creation(self):
        """Test creating memory edge with valid data"""
        now = datetime.now()
        memory = MemoryEdge(
            uuid="mem_123",
            fact="The merchant sells rare artifacts",
            valid_at=now,
            episode_ids=["ep_001"],
            source_node_uuid="node_001",
            target_node_uuid="node_002",
            agent_id="agent_001",
            memory_type=MemoryType.EPISODIC,
            session_number=1,
            days_elapsed=5
        )
        assert memory.uuid == "mem_123"
        assert memory.fact == "The merchant sells rare artifacts"
        assert memory.valid_at == now
        assert memory.invalid_at is None
        assert memory.episode_ids == ["ep_001"]
        assert memory.agent_id == "agent_001"
        assert memory.memory_type == MemoryType.EPISODIC.value
        assert memory.session_number == 1
        assert memory.days_elapsed == 5

    def test_temporal_consistency_valid_sequence(self):
        """Test valid_at before invalid_at is valid"""
        now = datetime.now()
        later = now + timedelta(hours=1)

        memory = MemoryEdge(
            uuid="mem_123",
            fact="Test fact",
            valid_at=now,
            invalid_at=later,
            episode_ids=["ep_001"],
            source_node_uuid="node_001",
            target_node_uuid="node_002",
            agent_id="agent_001",
            memory_type=MemoryType.EPISODIC,
            session_number=1,
            days_elapsed=0
        )
        assert memory.valid_at == now
        assert memory.invalid_at == later

    def test_temporal_consistency_invalid_sequence(self):
        """Test invalid_at before or equal to valid_at raises ValidationError"""
        now = datetime.now()
        earlier = now - timedelta(hours=1)

        with pytest.raises(ValidationError) as exc_info:
            MemoryEdge(
                uuid="mem_123",
                fact="Test fact",
                valid_at=now,
                invalid_at=earlier,
                episode_ids=["ep_001"],
                source_node_uuid="node_001",
                target_node_uuid="node_002",
                agent_id="agent_001",
                memory_type=MemoryType.EPISODIC,
                session_number=1,
                days_elapsed=0
            )
        assert "invalid_at" in str(exc_info.value)
        assert "must be after valid_at" in str(exc_info.value)

    def test_temporal_consistency_equal_times(self):
        """Test invalid_at equal to valid_at raises ValidationError"""
        now = datetime.now()

        with pytest.raises(ValidationError) as exc_info:
            MemoryEdge(
                uuid="mem_123",
                fact="Test fact",
                valid_at=now,
                invalid_at=now,
                episode_ids=["ep_001"],
                source_node_uuid="node_001",
                target_node_uuid="node_002",
                agent_id="agent_001",
                memory_type=MemoryType.EPISODIC,
                session_number=1,
                days_elapsed=0
            )
        assert "invalid_at" in str(exc_info.value)

    def test_invalid_at_none_is_valid(self):
        """Test invalid_at can be None (memory still valid)"""
        now = datetime.now()
        memory = MemoryEdge(
            uuid="mem_123",
            fact="Test fact",
            valid_at=now,
            invalid_at=None,
            episode_ids=["ep_001"],
            source_node_uuid="node_001",
            target_node_uuid="node_002",
            agent_id="agent_001",
            memory_type=MemoryType.EPISODIC,
            session_number=1,
            days_elapsed=0
        )
        assert memory.invalid_at is None

    def test_importance_range_validation(self):
        """Test importance must be between 0.0 and 1.0"""
        now = datetime.now()

        # Valid boundaries
        MemoryEdge(
            uuid="mem_123",
            fact="Test",
            valid_at=now,
            episode_ids=["ep_001"],
            source_node_uuid="node_001",
            target_node_uuid="node_002",
            agent_id="agent_001",
            memory_type=MemoryType.EPISODIC,
            session_number=1,
            days_elapsed=0,
            importance=0.0
        )
        MemoryEdge(
            uuid="mem_123",
            fact="Test",
            valid_at=now,
            episode_ids=["ep_001"],
            source_node_uuid="node_001",
            target_node_uuid="node_002",
            agent_id="agent_001",
            memory_type=MemoryType.EPISODIC,
            session_number=1,
            days_elapsed=0,
            importance=1.0
        )

        # Invalid: below 0
        with pytest.raises(ValidationError) as exc_info:
            MemoryEdge(
                uuid="mem_123",
                fact="Test",
                valid_at=now,
                episode_ids=["ep_001"],
                source_node_uuid="node_001",
                target_node_uuid="node_002",
                agent_id="agent_001",
                memory_type=MemoryType.EPISODIC,
                session_number=1,
                days_elapsed=0,
                importance=-0.1
            )
        assert "importance" in str(exc_info.value)

        # Invalid: above 1
        with pytest.raises(ValidationError) as exc_info:
            MemoryEdge(
                uuid="mem_123",
                fact="Test",
                valid_at=now,
                episode_ids=["ep_001"],
                source_node_uuid="node_001",
                target_node_uuid="node_002",
                agent_id="agent_001",
                memory_type=MemoryType.EPISODIC,
                session_number=1,
                days_elapsed=0,
                importance=1.5
            )
        assert "importance" in str(exc_info.value)

    def test_importance_default_value(self):
        """Test importance defaults to 0.5"""
        now = datetime.now()
        memory = MemoryEdge(
            uuid="mem_123",
            fact="Test",
            valid_at=now,
            episode_ids=["ep_001"],
            source_node_uuid="node_001",
            target_node_uuid="node_002",
            agent_id="agent_001",
            memory_type=MemoryType.EPISODIC,
            session_number=1,
            days_elapsed=0
        )
        assert memory.importance == 0.5

    def test_confidence_range_validation(self):
        """Test confidence must be between 0.0 and 1.0"""
        now = datetime.now()

        # Valid boundaries
        MemoryEdge(
            uuid="mem_123",
            fact="Test",
            valid_at=now,
            episode_ids=["ep_001"],
            source_node_uuid="node_001",
            target_node_uuid="node_002",
            agent_id="agent_001",
            memory_type=MemoryType.EPISODIC,
            session_number=1,
            days_elapsed=0,
            confidence=0.0
        )
        MemoryEdge(
            uuid="mem_123",
            fact="Test",
            valid_at=now,
            episode_ids=["ep_001"],
            source_node_uuid="node_001",
            target_node_uuid="node_002",
            agent_id="agent_001",
            memory_type=MemoryType.EPISODIC,
            session_number=1,
            days_elapsed=0,
            confidence=1.0
        )

        # Invalid values
        with pytest.raises(ValidationError):
            MemoryEdge(
                uuid="mem_123",
                fact="Test",
                valid_at=now,
                episode_ids=["ep_001"],
                source_node_uuid="node_001",
                target_node_uuid="node_002",
                agent_id="agent_001",
                memory_type=MemoryType.EPISODIC,
                session_number=1,
                days_elapsed=0,
                confidence=-0.1
            )

    def test_confidence_default_value(self):
        """Test confidence defaults to 1.0"""
        now = datetime.now()
        memory = MemoryEdge(
            uuid="mem_123",
            fact="Test",
            valid_at=now,
            episode_ids=["ep_001"],
            source_node_uuid="node_001",
            target_node_uuid="node_002",
            agent_id="agent_001",
            memory_type=MemoryType.EPISODIC,
            session_number=1,
            days_elapsed=0
        )
        assert memory.confidence == 1.0

    def test_rehearsal_count_validation(self):
        """Test rehearsal_count must be >= 0"""
        now = datetime.now()

        # Valid: 0 and positive
        MemoryEdge(
            uuid="mem_123",
            fact="Test",
            valid_at=now,
            episode_ids=["ep_001"],
            source_node_uuid="node_001",
            target_node_uuid="node_002",
            agent_id="agent_001",
            memory_type=MemoryType.EPISODIC,
            session_number=1,
            days_elapsed=0,
            rehearsal_count=0
        )
        MemoryEdge(
            uuid="mem_123",
            fact="Test",
            valid_at=now,
            episode_ids=["ep_001"],
            source_node_uuid="node_001",
            target_node_uuid="node_002",
            agent_id="agent_001",
            memory_type=MemoryType.EPISODIC,
            session_number=1,
            days_elapsed=0,
            rehearsal_count=100
        )

        # Invalid: negative
        with pytest.raises(ValidationError) as exc_info:
            MemoryEdge(
                uuid="mem_123",
                fact="Test",
                valid_at=now,
                episode_ids=["ep_001"],
                source_node_uuid="node_001",
                target_node_uuid="node_002",
                agent_id="agent_001",
                memory_type=MemoryType.EPISODIC,
                session_number=1,
                days_elapsed=0,
                rehearsal_count=-1
            )
        assert "rehearsal_count" in str(exc_info.value)

    def test_rehearsal_count_default_value(self):
        """Test rehearsal_count defaults to 0"""
        now = datetime.now()
        memory = MemoryEdge(
            uuid="mem_123",
            fact="Test",
            valid_at=now,
            episode_ids=["ep_001"],
            source_node_uuid="node_001",
            target_node_uuid="node_002",
            agent_id="agent_001",
            memory_type=MemoryType.EPISODIC,
            session_number=1,
            days_elapsed=0
        )
        assert memory.rehearsal_count == 0

    def test_session_number_validation(self):
        """Test session_number must be >= 1"""
        now = datetime.now()

        # Valid
        MemoryEdge(
            uuid="mem_123",
            fact="Test",
            valid_at=now,
            episode_ids=["ep_001"],
            source_node_uuid="node_001",
            target_node_uuid="node_002",
            agent_id="agent_001",
            memory_type=MemoryType.EPISODIC,
            session_number=1,
            days_elapsed=0
        )

        # Invalid: 0
        with pytest.raises(ValidationError) as exc_info:
            MemoryEdge(
                uuid="mem_123",
                fact="Test",
                valid_at=now,
                episode_ids=["ep_001"],
                source_node_uuid="node_001",
                target_node_uuid="node_002",
                agent_id="agent_001",
                memory_type=MemoryType.EPISODIC,
                session_number=0,
                days_elapsed=0
            )
        assert "session_number" in str(exc_info.value)

    def test_days_elapsed_validation(self):
        """Test days_elapsed must be >= 0"""
        now = datetime.now()

        # Valid
        MemoryEdge(
            uuid="mem_123",
            fact="Test",
            valid_at=now,
            episode_ids=["ep_001"],
            source_node_uuid="node_001",
            target_node_uuid="node_002",
            agent_id="agent_001",
            memory_type=MemoryType.EPISODIC,
            session_number=1,
            days_elapsed=0
        )

        # Invalid: negative
        with pytest.raises(ValidationError) as exc_info:
            MemoryEdge(
                uuid="mem_123",
                fact="Test",
                valid_at=now,
                episode_ids=["ep_001"],
                source_node_uuid="node_001",
                target_node_uuid="node_002",
                agent_id="agent_001",
                memory_type=MemoryType.EPISODIC,
                session_number=1,
                days_elapsed=-1
            )
        assert "days_elapsed" in str(exc_info.value)

    def test_memory_type_enum_values(self):
        """Test all MemoryType enum values are valid"""
        now = datetime.now()

        for mem_type in [MemoryType.EPISODIC, MemoryType.SEMANTIC, MemoryType.PROCEDURAL]:
            memory = MemoryEdge(
                uuid="mem_123",
                fact="Test",
                valid_at=now,
                episode_ids=["ep_001"],
                source_node_uuid="node_001",
                target_node_uuid="node_002",
                agent_id="agent_001",
                memory_type=mem_type,
                session_number=1,
                days_elapsed=0
            )
            # use_enum_values=True means we get the string value
            assert memory.memory_type in ["episodic", "semantic", "procedural"]

    def test_corruption_type_enum_values(self):
        """Test all CorruptionType enum values are valid"""
        now = datetime.now()

        corruption_types = [
            CorruptionType.DETAIL_DRIFT,
            CorruptionType.EMOTIONAL_COLORING,
            CorruptionType.CONFLATION,
            CorruptionType.SIMPLIFICATION,
            CorruptionType.FALSE_CONFIDENCE
        ]

        for corr_type in corruption_types:
            memory = MemoryEdge(
                uuid="mem_123",
                fact="Test",
                valid_at=now,
                episode_ids=["ep_001"],
                source_node_uuid="node_001",
                target_node_uuid="node_002",
                agent_id="agent_001",
                memory_type=MemoryType.EPISODIC,
                session_number=1,
                days_elapsed=0,
                corruption_type=corr_type
            )
            # use_enum_values=True means we get the string value
            assert isinstance(memory.corruption_type, str)

    def test_corruption_fields_optional(self):
        """Test corruption_type and original_uuid are optional"""
        now = datetime.now()
        memory = MemoryEdge(
            uuid="mem_123",
            fact="Test",
            valid_at=now,
            episode_ids=["ep_001"],
            source_node_uuid="node_001",
            target_node_uuid="node_002",
            agent_id="agent_001",
            memory_type=MemoryType.EPISODIC,
            session_number=1,
            days_elapsed=0
        )
        assert memory.corruption_type is None
        assert memory.original_uuid is None
        assert memory.corruption_probability is None

    def test_corruption_probability_range_validation(self):
        """Test corruption_probability must be between 0.0 and 1.0 if provided"""
        now = datetime.now()

        # Valid
        MemoryEdge(
            uuid="mem_123",
            fact="Test",
            valid_at=now,
            episode_ids=["ep_001"],
            source_node_uuid="node_001",
            target_node_uuid="node_002",
            agent_id="agent_001",
            memory_type=MemoryType.EPISODIC,
            session_number=1,
            days_elapsed=0,
            corruption_probability=0.7
        )

        # Invalid
        with pytest.raises(ValidationError):
            MemoryEdge(
                uuid="mem_123",
                fact="Test",
                valid_at=now,
                episode_ids=["ep_001"],
                source_node_uuid="node_001",
                target_node_uuid="node_002",
                agent_id="agent_001",
                memory_type=MemoryType.EPISODIC,
                session_number=1,
                days_elapsed=0,
                corruption_probability=1.5
            )

    def test_model_serialization_to_dict(self):
        """Test memory edge can be serialized to dict"""
        now = datetime.now()
        memory = MemoryEdge(
            uuid="mem_123",
            fact="The merchant sells rare artifacts",
            valid_at=now,
            episode_ids=["ep_001"],
            source_node_uuid="node_001",
            target_node_uuid="node_002",
            agent_id="agent_001",
            memory_type=MemoryType.EPISODIC,
            session_number=1,
            days_elapsed=5,
            importance=0.8,
            confidence=0.9
        )
        data = memory.model_dump()
        assert isinstance(data, dict)
        assert data["uuid"] == "mem_123"
        assert data["fact"] == "The merchant sells rare artifacts"
        assert data["memory_type"] == "episodic"
        assert data["importance"] == 0.8

    def test_required_fields(self):
        """Test all required fields must be provided"""
        with pytest.raises(ValidationError) as exc_info:
            MemoryEdge()
        error_str = str(exc_info.value)
        assert "uuid" in error_str
        assert "fact" in error_str
        assert "valid_at" in error_str


class TestCorruptionConfig:
    """Test suite for CorruptionConfig model"""

    def test_valid_config_creation(self):
        """Test creating corruption config with valid data"""
        config = CorruptionConfig(
            enabled=True,
            global_strength=0.7,
            corruption_types_enabled=[CorruptionType.DETAIL_DRIFT],
            min_days_before_corruption=10,
            important_memory_threshold=0.9,
            rehearsal_immunity_threshold=25
        )
        assert config.enabled is True
        assert config.global_strength == 0.7
        assert len(config.corruption_types_enabled) == 1

    def test_default_values(self):
        """Test corruption config has sensible defaults"""
        config = CorruptionConfig()
        assert config.enabled is False
        assert config.global_strength == 0.5
        assert config.min_days_before_corruption == 7
        assert config.important_memory_threshold == 0.8
        assert config.rehearsal_immunity_threshold == 20

    def test_global_strength_range_validation(self):
        """Test global_strength must be between 0.0 and 1.0"""
        CorruptionConfig(global_strength=0.0)
        CorruptionConfig(global_strength=1.0)

        with pytest.raises(ValidationError):
            CorruptionConfig(global_strength=1.5)
